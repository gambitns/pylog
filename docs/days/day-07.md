# Day 7 — Build the log: segments and the Log itself

- **Book:** Ch 3 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 9
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/log/log.py`
- `pylog/internal/log/segment.py`
- `tests/test_durable_log.py`

## What this day is about

Rolling to a new segment when maxed, setup from existing segments after a restart, append/read/truncate, reader() for snapshots. Same append/read shape as Day 1 — now durable.
