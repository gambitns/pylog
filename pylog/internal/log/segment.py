"""Chapter 3 — the segment: the abstraction tying a store and an index
together. A segment covers a contiguous range of offsets starting at
``base_offset``. Appending writes the record to the store, then writes
an index entry (relative offset, store position). Reading looks the
position up in the index, then reads the record from the store.

A segment is "maxed" when either its store or its index has reached
the configured max size — that is when the log rolls to a new segment.
"""

import os
import threading

from pylog.api.v1 import log_pb2

from .index import Index
from .store import Store


class Segment:
    def __init__(self, dir_path: str, base_offset: int, config) -> None:
        self.base_offset = base_offset
        self.config = config
        self._mu = threading.Lock()
        self.store = Store.open(os.path.join(dir_path, f"{base_offset}.store"))
        self.index = Index.open(
            os.path.join(dir_path, f"{base_offset}.index"),
            config.max_index_bytes,
        )
        # The next offset is base + number of entries already indexed
        # (recovered from the index file after a restart).
        rel, _ = self.index.read(-1) if self.index.size > 0 else (None, None)
        self.next_offset = base_offset if rel is None else base_offset + rel + 1

    def append(self, record: log_pb2.Record) -> int:
        with self._mu:
            offset = self.next_offset
            record.offset = offset
            data = record.SerializeToString()
            _, pos = self.store.append(data)
            self.index.write(offset - self.base_offset, pos)
            self.next_offset += 1
            return offset

    def read(self, offset: int) -> log_pb2.Record:
        with self._mu:
            _, pos = self.index.read(offset - self.base_offset)
            data = self.store.read(pos)
            record = log_pb2.Record()
            record.ParseFromString(data)
            return record

    def is_maxed(self) -> bool:
        return (
            self.store.size >= self.config.max_store_bytes
            or self.index.size >= self.config.max_index_bytes
        )

    def remove(self) -> None:
        self.close()
        for path in (self.store_path, self.index_path):
            try:
                os.remove(path)
            except FileNotFoundError:
                pass

    @property
    def store_path(self) -> str:
        return self.store._file.name

    @property
    def index_path(self) -> str:
        return self.index._file.name

    def close(self) -> None:
        self.store.close()
        self.index.close()
