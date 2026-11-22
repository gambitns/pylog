# Day 17 — Gossip and Serf, in Python terms

- **Book:** Ch 7 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 19
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/discovery/membership.py`
- `pylog/internal/discovery/serf.py`

## What this day is about

How membership spreads by rumour (push/pull, dedup by rumour ID). Pure-Python gossip to read; the real Serf agent driven from Python for the full build — Python has no mature Serf library.
