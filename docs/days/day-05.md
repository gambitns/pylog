# Day 5 — How logs work: store, index, segment

- **Book:** Ch 3 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 7
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/log/store.py`
- `pylog/internal/log/index.py`
- `pylog/internal/log/segment.py`

## What this day is about

Why a real log is three cooperating pieces, not one file: length-prefixed records, a fixed-width index, a segment tying them together.
