"""Day 2 — Chapter 1: a JSON over HTTP server on top of the Day 1 log.

Delivered in chat as Day 2 (2026-11-22). Two endpoints, both on ``/``:
produce (``POST /``) and consume (``GET /``). Go's ``net/http`` +
gorilla/mux becomes Python's stdlib ``http.server``; the handler logic
stays visible instead of hidden behind a framework.

Each handler is the same three steps: unmarshal the JSON body, run the
logic against the log, marshal and write the result.

Record values travel as base64 in JSON, in Go and in Python — Go's
``encoding/json`` encodes a ``[]byte`` as base64, so decode on the way
in and encode on the way out.

Error codes carry meaning: 400 for a bad request, 404 for a missing
offset, 500 for a server failure.

One quirk, carried over faithfully from the book: consume is a ``GET``
that carries a JSON body (``curl -X GET -d '{"offset": 0}'``). That works
with curl, but many HTTP clients won't send a body with a GET — one of
the reasons the book later replaces this transport with gRPC.

Wiring note (reconstruction fix): the chat snippet showed ``_Handler``
referring to ``self.server`` as the ``_HTTPServer`` holder, but
``BaseHTTPRequestHandler.server`` is always the ``ThreadingHTTPServer``
itself. ``new_http_server`` therefore attaches the holder to the HTTP
server as ``._holder`` and the dispatcher reads it from there. The
handler functions themselves are exactly as delivered in chat.
"""

import base64
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .log import Log, OffsetNotFoundError, Record


class _HTTPServer:
    """Holds the log the handlers defer to."""

    def __init__(self) -> None:
        self.log = Log()


def new_http_server(addr: str) -> ThreadingHTTPServer:
    host, port = addr.rsplit(":", 1)
    srv = ThreadingHTTPServer((host or "0.0.0.0", int(port)), _Handler)
    srv._holder = _HTTPServer()  # see wiring note above
    return srv


def _handle_produce(server: _HTTPServer, body: dict) -> tuple[int, dict]:
    # 1. Unmarshal: JSON body -> request.
    #    A missing "record" or a value that isn't valid base64 is a bad request.
    try:
        record_data = body["record"]
        # validate=True: without it, b64decode silently drops invalid
        # characters (e.g. "!!!" decodes to b""), so a bad value would
        # be accepted instead of returning 400 as the chat intends.
        value = base64.b64decode(record_data["value"], validate=True)
    except (KeyError, TypeError, ValueError):
        return 400, {"error": "invalid produce request"}

    # 2. Run the logic: append to the log, get the offset back.
    offset = server.log.append(Record(value=value))

    # 3. Marshal: result -> JSON response.
    return 200, {"offset": offset}


def _handle_consume(server: _HTTPServer, body: dict) -> tuple[int, dict]:
    # 1. Unmarshal.
    try:
        offset = body["offset"]
    except (KeyError, TypeError):
        return 400, {"error": "invalid consume request"}

    # 2. Run the logic.
    try:
        record = server.log.read(offset)
    except OffsetNotFoundError:
        return 404, {"error": "offset not found"}

    # 3. Marshal. Bytes go back out as base64, matching what produce accepted.
    return 200, {
        "record": {
            "value": base64.b64encode(record.value).decode("ascii"),
            "offset": record.offset,
        }
    }


class _Handler(BaseHTTPRequestHandler):
    def _dispatch(self, handler):
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length)) if length else {}
        except json.JSONDecodeError:
            return self._send(400, {"error": "invalid JSON"})
        try:
            status, payload = handler(self.server._holder, body)
        except Exception:  # any other failure is a 500, not a crash
            return self._send(500, {"error": "internal server error"})
        self._send(status, payload)

    def do_POST(self):
        self._dispatch(_handle_produce)

    def do_GET(self):
        self._dispatch(_handle_consume)

    def _send(self, status: int, payload: dict) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):  # keep the output quiet
        pass
