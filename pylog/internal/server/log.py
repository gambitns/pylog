"""Day 1 — Chapter 1: the in-memory commit-log prototype.

Delivered in chat as Day 1 of the course (book-style rewrite, 2026-11-22).
A commit log is an append-only sequence of records, ordered by time. You
append to the end, you read oldest to newest, and the log assigns each
record a sequential offset — that offset is its ID.

Go original (book, ``internal/server/log.go``): ``sync.Mutex`` + ``[]Record``.
Python: ``threading.Lock`` + ``list[Record]``. The lock is for the servers
that will call this log from different threads later (Days 2, 4+).
"""

import threading
from dataclasses import dataclass


@dataclass
class Record:
    value: bytes
    offset: int = 0


class OffsetNotFoundError(Exception):
    """The book's ``ErrOffsetNotFound`` — a missing offset is an error you
    can catch, not a silent empty result."""


class Log:
    def __init__(self) -> None:
        self._mu = threading.Lock()
        self._records: list[Record] = []

    def append(self, record: Record) -> int:
        with self._mu:
            record.offset = len(self._records)
            self._records.append(record)
            return record.offset

    def read(self, offset: int) -> Record:
        with self._mu:
            if offset < 0 or offset >= len(self._records):
                raise OffsetNotFoundError("offset not found")
            return self._records[offset]
