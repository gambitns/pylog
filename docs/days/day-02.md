# Day 2 — Build a JSON over HTTP Server

- **Book:** Ch 1 — *Distributed Services with Go*, Travis Jeffery
- **Handbook mapping:** Handbook Days 3-4
- **Status:** Shared in chat (2026-11-22)

## Files introduced / changed

- `pylog/internal/server/http.py`
- `cmd/server/main.py`

## What this day is about

Stdlib http.server (not FastAPI — the handbook's FastAPI plan was superseded by the chat course). Produce/consume on /, base64 values, 400/404/500. Consume is a GET with a JSON body, faithfully as in the book.

> This day was shared in chat exactly as written there; the code in this repo matches the chat version (see the module docstrings for the one wiring fix in Day 2's `new_http_server` and the negative-offset guard in Day 1's `read`).
