"""Chapter 3 — the store: the file that holds records.

Book (``internal/log/store.go``): a thin wrapper around a file. Each
record is written as an 8-byte big-endian length prefix (``lenWidth``)
followed by the record's bytes. Writes go through a buffered writer to
cut down system calls; reads flush the buffer first, so a record that
hasn't been flushed to disk yet is still readable.

Python: ``struct`` for the length prefix, ``io.BufferedWriter`` for
the buffer, ``os.pread`` for position reads (no seek needed).
"""

import io
import os
import struct
import threading

LEN_WIDTH = 8
_ENC = struct.Struct(">Q")  # big-endian uint64, the book's binary.BigEndian


class Store:
    def __init__(self, f: io.BufferedRandom) -> None:
        self._file = f
        self._size = os.fstat(f.fileno()).st_size
        self._buf = io.BufferedWriter(f, buffer_size=8192)
        self._mu = threading.Lock()

    @classmethod
    def open(cls, path: str) -> "Store":
        # buffering=0: a raw FileIO. Wrapping a default buffered file
        # in a second BufferedWriter would trap flushed bytes in the
        # inner buffer, invisible to os.pread.
        f = open(path, "a+b", buffering=0)
        return cls(f)

    @property
    def size(self) -> int:
        return self._size

    def append(self, p: bytes) -> tuple[int, int]:
        """Return (bytes_written, position) — position is where the record
        starts in the file; the segment uses it for the index entry."""
        with self._mu:
            pos = self._size
            self._buf.write(_ENC.pack(len(p)))
            self._buf.write(p)
            n = LEN_WIDTH + len(p)
            self._size += n
            return n, pos

    def read(self, pos: int) -> bytes:
        with self._mu:
            self._buf.flush()
            size_bytes = os.pread(self._file.fileno(), LEN_WIDTH, pos)
            if len(size_bytes) < LEN_WIDTH:
                raise EOFError(f"no record at position {pos}")
            (size,) = _ENC.unpack(size_bytes)
            data = os.pread(self._file.fileno(), size, pos + LEN_WIDTH)
            if len(data) < size:
                raise EOFError(f"truncated record at position {pos}")
            return data

    def read_at(self, off: int, size: int) -> bytes:
        """Raw read of ``size`` bytes at ``off`` — used by
        ``Log.reader()`` to stream the whole store."""
        with self._mu:
            self._buf.flush()
            return os.pread(self._file.fileno(), size, off)

    def close(self) -> None:
        with self._mu:
            self._buf.flush()
            self._file.close()
