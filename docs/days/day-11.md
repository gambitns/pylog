# Day 11 — Secure, steps 1-2: TLS and mutual TLS

- **Book:** Ch 5 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 13
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/server/tls.py`
- `testdata/certs/`
- `scripts/make_certs.sh`

## What this day is about

Be your own CA with cfssl (openssl fallback in the script). Server identity first, then client identity.
