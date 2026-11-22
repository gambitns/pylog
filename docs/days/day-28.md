# Day 28 — Deploy locally; Raft on a full domain name

- **Book:** Ch 10 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Day 30
- **Status:** Not yet shared

## Files introduced / changed

- `deploy/k8s/pylog.yaml`
- `deploy/helm/pylog/templates/statefulset.yaml`

## What this day is about

Three nodes on Kind; why Raft needs stable names (headless Service, StatefulSet).
