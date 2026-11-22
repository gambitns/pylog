# Day 12 — Secure, step 3: authorisation with ACLs

- **Book:** Ch 5 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 14
- **Status:** Not yet shared

## Files introduced / changed

- `pylog/internal/server/auth.py`
- `tests/test_discovery_balancer_acl.py`

## What this day is about

Authentication is not authorisation. A readable policy function first (root may do everything, nobody nothing); Casbin's Python port is the drop-in upgrade. Denied calls get PERMISSION_DENIED.
