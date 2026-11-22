# Day 22 — One port, several services: multiplexing

- **Book:** Ch 8 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 24
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/raft/multiplex.py`

## What this day is about

Routing gRPC and Raft traffic over one listener by peeking at the first byte — the book's cmux idea, in readable Python. Not a full cmux (no TLS termination).
