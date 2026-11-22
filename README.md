# pylog

A distributed commit-log service in Python — the project from
**_Distributed Services with Go_ by Travis Jeffery (Pragmatic
Bookshelf, 2021)**, rebuilt in Python for personal learning, one
digestible chunk a day.

The book builds a service called `proglog`: a commit log you can
append records to and read back by offset. That simple idea is the
spine of systems like Kafka. This repo is the Python version, called
`pylog`: it starts as a JSON-over-HTTP log in memory, gains Protocol
Buffers and gRPC, learns TLS and observability, then becomes genuinely
distributed with service discovery, Raft consensus and client-side
load balancing — and is finally deployed with Docker and Kubernetes,
locally and on GKE.

This is a study companion and adaptation, **not a reproduction of the
book's text**. See `NOTICE.md` for attribution. No license is claimed
over the book's code; this repo is for personal learning (leave the
license choice to the owner if it is ever shared).

## Quick start — Days 1–3

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

make compile   # regenerates pylog/api/v1/log_pb2.py + log_pb2_grpc.py
make test      # runs the whole test suite
```

Run the Day 2 JSON/HTTP server:

```sh
python -m cmd.server.main        # serving on :8080
```

In another terminal — the book's curl examples (base64 values are
`"Let's Go #1"`, `#2`, `#3`):

```sh
curl -X POST localhost:8080 -d '{"record": {"value": "TGV0J3MgR28gIzEK"}}'
curl -X POST localhost:8080 -d '{"record": {"value": "TGV0J3MgR28gIzIK"}}'
curl -X POST localhost:8080 -d '{"record": {"value": "TGV0J3MgR28gIzMK"}}'

curl -X GET localhost:8080 -d '{"offset": 0}'
curl -X GET localhost:8080 -d '{"offset": 1}'
curl -X GET localhost:8080 -d '{"offset": 2}'
curl -X GET localhost:8080 -d '{"offset": 99}'   # 404 {"error": "offset not found"}
```

Run the gRPC server (Chapter 4):

```sh
python -m cmd.grpc_server.main --addr 127.0.0.1:8400 --data-dir /tmp/pylog-data
```

Run a clustered agent (Chapters 7–8):

```sh
python -m cmd.agent.main --node-id node-1 --data-dir /tmp/pylog-1 --rpc-addr 127.0.0.1:8401
```

## The 32-day map

Days 1–3 are exactly what was shared in chat. The handbook's
32-chunk roadmap is reconciled with the chat course like this:

- **Chat Day 1** = handbook Day 1 (in-memory log prototype).
- **Chat Day 2** = handbook Days 3–4 compressed: the *full* JSON/HTTP
  server in one chunk, with stdlib `http.server` — **not** FastAPI.
  (The handbook planned FastAPI for Days 3–4; the chat course chose
  stdlib to stay close to the book's Go `net/http`, and that choice
  stands here.)
- **Chat Day 3** = handbook Days 5–6 compressed: the *full* protobuf
  chapter in one chunk.
- That compression frees three slots, used for: **repo Day 4**
  (handbook Day 2, project setup, written out in full), **repo
  Day 31** (capstone: run the whole cluster end to end) and
  **repo Day 32** (where next). Every handbook day is covered; see
  `docs/days/day-NN.md` for the per-day handbook mapping.

| Days | Part | Book chapters | What happens |
| --- | --- | --- | --- |
| 1–7 | 1 Get Started | Ch 1–3 | In-memory log, JSON/HTTP, protobuf, durable on-disk log |
| 8–15 | 2 Network | Ch 4–6 | gRPC, TLS/mTLS + ACLs, observability, checkpoint |
| 16–24 | 3 Distribute | Ch 7–9 | Gossip discovery, Raft, client load balancing |
| 25–32 | 4 Deploy | Ch 10–11 | Kind, Docker, Helm, GKE, capstone, where next |

Each `docs/days/day-NN.md` gives the day's title, book chapter,
handbook mapping, status (shared vs not yet shared), and the files
introduced or changed that day.

## Layout

```
pylog/
  api/v1/log.proto            # Record + Log service (Ch 2, 4, 9)
  api/v1/log_pb2.py           # generated — committed so the repo works without protoc
  api/v1/log_pb2_grpc.py      # generated gRPC stubs
  internal/server/
    log.py                    # Day 1 in-memory Log
    http.py                   # Day 2 JSON/HTTP server
    grpc_server.py client.py  # Ch 4 gRPC servicer + client
    tls.py auth.py            # Ch 5 TLS/mTLS + ACLs
    observability.py          # Ch 6 metrics / logs / traces
  internal/log/               # Ch 3 durable log: store, index, segment, Log
  internal/discovery/         # Ch 7 gossip membership + real Serf driver
  internal/raft/              # Ch 8 Raft core, FSM, multiplexing
  internal/loadbalancer/      # Ch 9 resolver + pickers
  internal/agent/             # Ch 7–8 agent: ties it all together
cmd/server/main.py            # Day 2 entry point
cmd/grpc_server/main.py       # Ch 4 entry point
cmd/agent/main.py             # Ch 10 agent CLI
tests/                        # unittest suite (see Verification below)
deploy/                       # Dockerfile, Kind, k8s manifests, Helm chart, GKE notes
testdata/certs/               # Ch 5 CFSSL configs (generated *.pem is git-ignored)
docs/days/day-01.md … day-32.md
```

## Go → Python translation notes

| In the book (Go) | Here (Python) | What changes |
| --- | --- | --- |
| `net/http` + gorilla/mux, JSON | stdlib `http.server` | One method per HTTP verb; handler logic stays visible. |
| Protocol Buffers + `protoc` | `protobuf` + `grpc_tools.protoc` | Same `.proto` files. The Go-only `option go_package` line is dropped. `make compile` also runs `--grpc_python_out` (the Day 3 draft's Makefile only had `--python_out`, before the service existed). |
| gRPC-Go | `grpcio` | Same service definitions and stubs; servers run on a thread pool. |
| Goroutines and channels | threads / `threading.Lock` | `asyncio.Queue` is the closest channel equivalent; named where used. |
| TLS / mTLS, ACLs (Casbin) | `ssl` via grpcio credentials; readable policy function, Casbin optional | Certificates are made the same way (CFSSL; `scripts/make_certs.sh`, openssl fallback). |
| Zap logging, Prometheus, OpenTelemetry | stdlib `logging` (JSON lines), `prometheus_client`, `opentelemetry-sdk` (optional) | Same three telemetry kinds. |
| Serf for discovery | Gossip concepts in pure Python; a Serf agent driven from Python | **Differs in kind.** Python has no mature Serf library. You read a small gossip implementation, then call the real agent for the full build. |
| HashiCorp Raft (Go library) | Raft concepts in pure Python; `pysyncobj` named as the maintained-library option | **Differs in kind.** There is no drop-in Python port. The repo's Raft core is compact and readable and is tested (election, replication, commit); it is a teaching implementation, not a production consensus library. |
| Docker, Helm, Kubernetes, GKE | Identical tools | Only the Dockerfile's base image and start command change. |

**Honest limit** (handbook p.3): Go is the stronger language for this
kind of service in production — static types, a single binary, mature
Raft and discovery libraries. Python is the better learning vehicle
here because the distributed-systems ideas stay in the foreground and
the language stays out of the way.

### Two differences from other drafts — read before comparing files

1. **Day 2 consume uses a JSON body** (`curl -X GET -d '{"offset": 0}'`),
   exactly as delivered in chat and as in the book. An earlier verified
   draft (`ch1-python-verified/log_server.py` in the course goal files,
   *not* in this repo) used `?offset=N` on the query string instead;
   that file is not canonical here.
2. **Day 2 wiring fix.** The chat snippet showed the handler reading
   `self.server` as the `_HTTPServer` holder, but
   `BaseHTTPRequestHandler.server` is always the `ThreadingHTTPServer`
   itself. `new_http_server` therefore attaches the holder as
   `srv._holder` and the dispatcher reads it from there; the handler
   functions are unchanged. This is noted in `http.py`'s docstring.
   Day 1's `read` also guards negative offsets (the chat version only
   checked the upper bound; a negative index would have silently read
   from the end of the list). Day 2's produce handler decodes base64
   with `validate=True`: without it, `b64decode` silently drops
   invalid characters (e.g. `"!!!"` decodes to `b""`), so a bad value
   would have been accepted instead of returning 400 as the chat
   intends.

## Verification

What was actually run (see the commit for the exact run):

- `make test` — full unittest suite: Days 1–3, durable log
  (append/read, restart, reader, truncate, segment rollover), gRPC
  end-to-end (produce/consume/streams, durable persistence across
  restart), Raft (election, replication, commit, vote rules),
  gossip membership, pickers, ACL authorizer.
- Day 2 server + the book's curl examples (produce 3 records,
  consume them back, 404 on offset 99) — via the live-server test
  and a manual curl run.
- Protobuf round-trip: `Record(b"Let's Go #1", 0)` serializes to
  **13 bytes** (`b"\n\x0bLet's Go #1"`), vs 54 bytes as Day 2 JSON.

Readable but **not fully run**: Kubernetes/Kind/Helm/GKE manifests
(no cluster in this environment), the real Serf agent binary (not
installed; the pure-Python gossip is tested instead), mTLS end-to-end
with generated certificates (helpers + scripts are present; the ACL
authorizer itself is tested), and OpenTelemetry export (guarded
optional import; no collector here).

Sandbox note on the gRPC tests: in this VM the grpc C-core's TCP
loopback connections are intercepted by the environment's egress
proxy — a raw-socket probe showed the server speaking correct HTTP/2
while the grpc client never reached the listener and got ASCII
garbage back. The gRPC tests therefore run over Unix sockets (same
servicer, stubs and client code; on a normal machine TCP loopback
works, as the manual curl check of the HTTP server shows). The Day 2
server itself was verified over real TCP with curl.

## Status

Days 1–3 were shared in chat; Days 4–32 are written in this repo and
in `docs/days/` but have not been shared as daily chunks yet. The repo
is local-only: it has **not** been pushed to GitHub (no GitHub
connection is set up here). Pushing needs a repo name, visibility,
and a connected GitHub account — the next step for the owner.
