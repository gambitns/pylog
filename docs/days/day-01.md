# Day 1 — Let's Go: a log you can append to

- **Book:** Ch 1 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 1
- **Status:** Shared in chat (book-style rewrite, 2026-11-22)

## Files introduced / changed

- `pylog/internal/server/log.py`

## What this day is about

The in-memory Log: Record dataclass, OffsetNotFoundError, threading.Lock. Offset is the record's ID.

> This day was shared in chat exactly as written there; the code in this repo matches the chat version (see the module docstrings for the one wiring fix in Day 2's `new_http_server` and the negative-offset guard in Day 1's `read`).
