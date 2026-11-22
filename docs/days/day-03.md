# Day 3 — Structure Data with Protocol Buffers

- **Book:** Ch 2 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Days 5-6
- **Status:** Shared in chat (2026-11-22); code verified in draft day-03-protobuf.md

## Files introduced / changed

- `pylog/api/v1/log.proto`
- `pylog/api/v1/log_pb2.py`
- `Makefile`
- `tests/test_record_proto.py`

## What this day is about

Record as protobuf: 13 bytes on the wire vs 54 as Day 2 JSON. Field numbers are the wire identity; old readers ignore new fields.

> This day was shared in chat exactly as written there; the code in this repo matches the chat version (see the module docstrings for the one wiring fix in Day 2's `new_http_server` and the negative-offset guard in Day 1's `read`).
