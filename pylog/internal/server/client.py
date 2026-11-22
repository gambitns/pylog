"""Chapter 4 — the gRPC client.

Book (``api/v1/log_grpc.go`` is generated; the client usage is in the
tests): dial the server, call Produce / Consume, and stream with
ConsumeStream. The book's client wraps the generated stub; so does
this one, so the rest of the code (replication in Chapter 7, the
load-balanced client in Chapter 9) talks to a small, stable surface.
"""

import grpc

from pylog.api.v1 import log_pb2, log_pb2_grpc


class Client:
    def __init__(self, addr: str, credentials=None) -> None:
        if credentials is not None:
            self._channel = grpc.secure_channel(addr, credentials)
        else:
            self._channel = grpc.insecure_channel(addr)
        self._stub = log_pb2_grpc.LogStub(self._channel)

    def close(self) -> None:
        self._channel.close()

    def produce(self, value: bytes) -> int:
        resp = self._stub.Produce(
            log_pb2.ProduceRequest(record=log_pb2.Record(value=value))
        )
        return resp.offset

    def consume(self, offset: int) -> log_pb2.Record:
        return self._stub.Consume(
            log_pb2.ConsumeRequest(offset=offset)
        ).record

    def consume_stream(self, offset: int):
        for resp in self._stub.ConsumeStream(
            log_pb2.ConsumeRequest(offset=offset)
        ):
            yield resp.record

    def produce_stream(self, values):
        def requests():
            for value in values:
                yield log_pb2.ProduceRequest(
                    record=log_pb2.Record(value=value)
                )

        for resp in self._stub.ProduceStream(requests()):
            yield resp.offset

    def get_servers(self) -> list:
        return list(
            self._stub.GetServers(log_pb2.GetServersRequest()).servers
        )
