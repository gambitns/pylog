# Day 20 — Read a Raft core in Python

- **Book:** Ch 8 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 22
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/raft/raft.py`
- `tests/test_raft.py`

## What this day is about

RequestVote and AppendEntries in a compact readable implementation. No drop-in Python port of HashiCorp Raft exists; pysyncobj is the maintained-library option (see the day note).
