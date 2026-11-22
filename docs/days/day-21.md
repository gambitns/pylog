# Day 21 — Put consensus under pylog

- **Book:** Ch 8 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 23
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/raft/fsm.py`
- `pylog/internal/agent/agent.py`

## What this day is about

A state machine over your Log; writes go through Raft (propose), never straight to the log, once clustered. Snapshot/restore via Log.reader().
