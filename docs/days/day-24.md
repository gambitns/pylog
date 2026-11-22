# Day 24 — Resolvers and pickers in gRPC Python

- **Book:** Ch 9 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 26
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/loadbalancer/balancer.py`

## What this day is about

Discovering servers from the client (GetServers); routing produce to the leader and consume across the followers. grpcio has no Go-style resolver/picker plugin API, so this is a small client-side layer over the stubs — same ideas, not the Go API surface.
