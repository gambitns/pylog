"""Chapter 3 — the index: the file that finds records fast.

Book (``internal/log/index.go``): each entry is fixed-width, 12 bytes
(``entWidth``): a 4-byte relative offset (``offWidth``, uint32 — the
record's offset minus the segment's base offset) followed by an
8-byte position (``posWidth``, uint64 — where the record sits in the
store file). Because entries are fixed-width, the entry for a relative
offset is at byte ``offset * entWidth`` — a direct jump, no scan.

The book memory-maps the file (``gommap``) and grows it to the max
index size up front, then truncates it back to the entries actually
written on close. On reopen, the file's real size *is* the number of
entries written — that is how the index knows its size after a restart,
with no scanning. Python's ``mmap`` module does the same.
"""

import mmap
import os
import struct
import threading

OFF_WIDTH = 4
POS_WIDTH = 8
ENT_WIDTH = OFF_WIDTH + POS_WIDTH
_ENC_OFF = struct.Struct(">I")  # big-endian uint32
_ENC_POS = struct.Struct(">Q")  # big-endian uint64


class Index:
    def __init__(self, f, max_bytes: int) -> None:
        self._file = f
        self._mu = threading.Lock()
        # The file's real size is the entries written so far (close()
        # truncates to exactly that). Capture it *before* growing.
        self._size = os.fstat(f.fileno()).st_size
        f.truncate(max_bytes)
        self._mmap = mmap.mmap(f.fileno(), max_bytes, access=mmap.ACCESS_WRITE)

    @classmethod
    def open(cls, path: str, max_bytes: int) -> "Index":
        f = open(path, "a+b", buffering=0)
        return cls(f, max_bytes)

    @property
    def size(self) -> int:
        return self._size

    def read(self, off: int) -> tuple[int, int]:
        """Return (relative_offset, position) for relative offset ``off``.
        ``off == -1`` reads the last entry, as in the book."""
        with self._mu:
            if self._size == 0:
                raise EOFError("index is empty")
            if off == -1:
                pos = self._size - ENT_WIDTH
            else:
                pos = off * ENT_WIDTH
            if pos + ENT_WIDTH > self._size:
                raise EOFError(f"no index entry for offset {off}")
            rel = _ENC_OFF.unpack_from(self._mmap, pos)[0]
            store_pos = _ENC_POS.unpack_from(self._mmap, pos + OFF_WIDTH)[0]
            return rel, store_pos

    def write(self, off: int, pos: int) -> None:
        with self._mu:
            if self._size + ENT_WIDTH > len(self._mmap):
                raise EOFError("index is full")
            _ENC_OFF.pack_into(self._mmap, self._size, off)
            _ENC_POS.pack_into(self._mmap, self._size + OFF_WIDTH, pos)
            self._size += ENT_WIDTH

    def close(self) -> None:
        with self._mu:
            self._mmap.flush()
            # Shrink the file back to the entries actually written.
            self._file.truncate(self._size)
            self._mmap.close()
            self._file.close()
