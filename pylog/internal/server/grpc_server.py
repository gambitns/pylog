"""Chapter 4 — the gRPC server.

Book (``internal/server/server.go``): the compiler generates the server
stub from ``log.proto``; our job is the struct whose methods match the
service definition. ``grpcio`` generates ``log_pb2_grpc.LogServicer``
the same way.

Design points from the book, kept here:
* The servicer takes a ``CommitLog`` (anything with ``append``/``read``)
  — dependency inversion with an interface, so tests can pass the
  in-memory log and production passes the durable one. In Python that
  is a duck-typed protocol (``typing.Protocol``), not a Go interface.
* Errors are gRPC status codes, not HTTP codes: ``INVALID_ARGUMENT``
  for a bad request, ``NOT_FOUND`` for a missing offset — the same
  distinction Day 2 made with 400/404.
* ``ConsumeStream`` is server-side streaming: read from the requested
  offset to the end of the log, yielding each record.
* ``ProduceStream`` is bidirectional streaming, answered in lockstep:
  one response per request.
* ``GetServers`` (Chapter 9) reports the servers this node knows about
  and which one is the leader; the resolver uses it.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Protocol

import grpc

from pylog.api.v1 import log_pb2, log_pb2_grpc


class CommitLog(Protocol):
    def append(self, record) -> int: ...
    def read(self, offset: int): ...


class LogServicer(log_pb2_grpc.LogServicer):
    def __init__(self, log: CommitLog, servers: list | None = None) -> None:
        self.log = log
        self._servers = servers or []

    # -- unary ---------------------------------------------------------
    def Produce(self, request, context):
        record = request.record
        try:
            offset = self.log.append(record)
        except Exception as exc:  # noqa: BLE001 — surface as INTERNAL
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return log_pb2.ProduceResponse()
        return log_pb2.ProduceResponse(offset=offset)

    def Consume(self, request, context):
        try:
            record = self.log.read(request.offset)
        except Exception:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"offset not found: {request.offset}")
            return log_pb2.ConsumeResponse()
        return log_pb2.ConsumeResponse(record=record)

    def GetServers(self, request, context):
        return log_pb2.GetServersResponse(servers=self._servers)

    # -- streaming -----------------------------------------------------
    def ConsumeStream(self, request, context):
        offset = request.offset
        while True:
            try:
                record = self.log.read(offset)
            except Exception:
                return
            yield log_pb2.ConsumeResponse(record=record)
            offset += 1

    def ProduceStream(self, request_iterator, context):
        for request in request_iterator:
            try:
                offset = self.log.append(request.record)
            except Exception as exc:  # noqa: BLE001
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(str(exc))
                return
            yield log_pb2.ProduceResponse(offset=offset)


def new_grpc_server(log: CommitLog, addr: str | None = "[::]:8080",
                    servers: list | None = None,
                    interceptors: list | None = None,
                    credentials=None) -> grpc.Server:
    """Create (but do not start) the gRPC server. Pass ``credentials``
    for TLS (Chapter 5); without them the server is insecure, as in
    Chapter 4. Pass ``addr=None`` to skip binding (tests bind their
    own ephemeral port)."""
    server = grpc.server(
        ThreadPoolExecutor(max_workers=10),
        interceptors=interceptors or [],
    )
    log_pb2_grpc.add_LogServicer_to_server(LogServicer(log, servers), server)
    if addr is not None:
        if credentials is not None:
            server.add_secure_port(addr, credentials)
        else:
            server.add_insecure_port(addr)
    return server
