# Day 6 — Build the log: store and index

- **Book:** Ch 3 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 8
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/log/store.py`
- `pylog/internal/log/index.py`

## What this day is about

Store: 8-byte big-endian length prefix + bytes, buffered writer, flush before read. Index: 12-byte entries (4-byte relative offset + 8-byte position), mmap, grown to max size and truncated back on close.
