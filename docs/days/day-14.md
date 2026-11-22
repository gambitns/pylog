# Day 14 — Make pylog observable

- **Book:** Ch 6 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 16
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/server/observability.py`

## What this day is about

Prometheus metrics on :2112/metrics, one JSON log line per RPC, OpenTelemetry tracing wired as an interceptor (optional dependency, guarded import).
