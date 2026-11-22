"""Chapter 3 — the Log: the abstraction tying all the segments together.

Book (``internal/log/log.go``). The Day 1 in-memory ``Log`` kept the
same ``append`` / ``read`` shape; this one makes it durable:

* ``append`` serializes the record (protobuf, from Day 3), appends it
  to the active segment, and rolls to a new segment when the active
  one is maxed.
* ``read`` finds the segment containing the offset and reads from it.
* ``truncate`` drops every segment whose records are all below the
  given lowest offset.
* ``reader`` streams the whole log as raw length-prefixed bytes, so a
  follower (Chapters 7-8) can snapshot and restore it.
* A new ``Log`` on an existing directory bootstraps itself from the
  segments already on disk (``setup``).

Config defaults are the book's: a segment holds at most 1024 bytes of
store and 1024 bytes of index unless you say otherwise.
"""

import io
import os
import threading
from dataclasses import dataclass, field

from pylog.api.v1 import log_pb2

from .segment import Segment
from .store import LEN_WIDTH


class OffsetOutOfRangeError(Exception):
    """The durable log's ``ErrOffsetOutOfRange``."""


@dataclass
class SegmentConfig:
    max_store_bytes: int = 1024
    max_index_bytes: int = 1024
    initial_offset: int = 0


@dataclass
class Config:
    segment: SegmentConfig = field(default_factory=SegmentConfig)


class Log:
    def __init__(self, dir_path: str, config: Config | None = None) -> None:
        self.dir = dir_path
        self.config = config or Config()
        self._mu = threading.Lock()
        self._segments: list[Segment] = []
        self._active_segment: Segment | None = None
        os.makedirs(dir_path, exist_ok=True)
        self._setup()

    # -- setup ---------------------------------------------------------
    def _setup(self) -> None:
        base_offsets = set()
        for name in os.listdir(self.dir):
            base, ext = os.path.splitext(name)
            if ext in (".store", ".index") and base.isdigit():
                base_offsets.add(int(base))
        for base in sorted(base_offsets):
            self._new_segment(base)
        if not self._segments:
            self._new_segment(self.config.segment.initial_offset)

    def _new_segment(self, base_offset: int) -> None:
        seg = Segment(self.dir, base_offset, self.config.segment)
        self._segments.append(seg)
        self._active_segment = seg

    # -- public API ----------------------------------------------------
    def append(self, record: log_pb2.Record) -> int:
        with self._mu:
            if self._active_segment.is_maxed():
                self._new_segment(self._active_segment.next_offset)
            return self._active_segment.append(record)

    def read(self, offset: int) -> log_pb2.Record:
        with self._mu:
            for seg in self._segments:
                if seg.base_offset <= offset < seg.next_offset:
                    return seg.read(offset)
            raise OffsetOutOfRangeError(f"offset out of range: {offset}")

    def truncate(self, lowest: int) -> None:
        """Drop every segment whose highest offset is below ``lowest``
        — i.e. segments with ``next_offset <= lowest + 1``, as in the
        book."""
        with self._mu:
            kept = []
            for seg in self._segments:
                if seg.next_offset <= lowest + 1:
                    seg.remove()
                else:
                    kept.append(seg)
            self._segments = kept
            if self._segments:
                self._active_segment = self._segments[-1]

    def lowest_offset(self) -> int:
        with self._mu:
            return self._segments[0].base_offset

    def highest_offset(self) -> int:
        with self._mu:
            if self._active_segment.next_offset == self._active_segment.base_offset:
                return 0
            return self._active_segment.next_offset - 1

    def reader(self) -> io.BytesIO:
        """The whole log as raw bytes, segment by segment, store by
        store — each record still length-prefixed, exactly as on disk.
        A reader skips the 8-byte length prefix of the first record
        when unmarshalling (see the book's ``testReader``)."""
        with self._mu:
            out = io.BytesIO()
            for seg in self._segments:
                out.write(seg.store.read_at(0, seg.store.size))
            out.seek(0)
            return out

    def close(self) -> None:
        with self._mu:
            for seg in self._segments:
                seg.close()
