"""Chapter 8 — multiplexing: several services on one port.

The book uses ``cmux`` (Go) so the gRPC server *and* the Raft stream
layer share a single listener: cmux peeks at the first bytes of each
connection and routes it to the right handler. The benefit is
operational — one port to document, firewall and expose — not
algorithmic.

Python has no cmux equivalent. This module is the honest, readable
version of the same idea: a TCP listener that peeks at the first byte
of a connection and dispatches it.

* gRPC (HTTP/2) connections start with the HTTP/2 connection preface
  ``PRI * HTTP/2.0`` — first byte ``P`` (0x50).
* Raft stream-layer connections in this codebase start with a
  one-byte magic, ``0x01``, followed by a length-prefixed message.

``MultiplexedListener`` accepts connections, peeks, and hands the
socket to the registered handler for that prefix. The agent uses it
so Raft and gRPC share ``:8400`` (the book's single port) while the
code stays readable. It is *not* a full cmux: it does not do TLS
termination or HTTP/1 routing, and it says so here rather than in a
footnote.
"""

import socket
import threading

RAFT_MAGIC = b"\x01"
GRPC_PREFACE_PREFIX = b"PRI * HTTP/2.0"


class MultiplexedListener:
    def __init__(self, addr: tuple[str, int]) -> None:
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind(addr)
        self._sock.listen(128)
        self._handlers: dict[bytes, callable] = {}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def register(self, prefix: bytes, handler) -> None:
        """``handler`` receives the accepted socket; the peeked byte
        is still in the stream (``MSG_PEEK`` does not consume it)."""
        self._handlers[prefix] = handler

    def serve_forever(self) -> None:
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except OSError:
                return
            threading.Thread(target=self._dispatch, args=(conn,), daemon=True).start()

    def _dispatch(self, conn: socket.socket) -> None:
        try:
            peeked = conn.recv(1, socket.MSG_PEEK)
            if not peeked:
                conn.close()
                return
            for prefix, handler in self._handlers.items():
                if peeked.startswith(prefix[:1]):
                    handler(conn)
                    return
            conn.close()  # unknown protocol — close, don't guess
        except OSError:
            try:
                conn.close()
            except OSError:
                pass

    def close(self) -> None:
        self._stop.set()
        self._sock.close()
