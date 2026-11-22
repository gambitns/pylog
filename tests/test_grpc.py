"""Chapter 4 — gRPC end-to-end: produce / consume / streams against
an in-process server (the book's test pattern: start a server, drive
it with the real client).

Transport note: these tests run over a Unix socket, not TCP loopback.
In this sandbox the grpc C-core's TCP loopback connections are
intercepted by the environment's egress proxy (the client never
reaches the listener and gets ASCII garbage back — verified with a
raw-socket probe), while the same server speaks correct HTTP/2 over
a plain socket and grpc over a Unix socket works. The servicer,
stubs and client code under test are identical either way; on a
normal machine TCP loopback works — see README's Verification note.
"""
import os
import tempfile
import unittest

import grpc

from pylog.internal.log import Log as DurableLog
from pylog.internal.server.client import Client
from pylog.internal.server.grpc_server import new_grpc_server
from pylog.internal.server.log import Log as MemoryLog


def _unix_target(tmpdir: str, name: str) -> str:
    return f"unix://{os.path.join(tmpdir, name)}.sock"


class TestGrpc(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.log = MemoryLog()
        self.server = new_grpc_server(self.log, addr=None)
        self.target = _unix_target(self._tmp.name, "grpc")
        self.server.add_insecure_port(self.target)
        self.server.start()
        self.client = Client(self.target)

    def tearDown(self):
        self.client.close()
        self.server.stop(grace=0)
        self._tmp.cleanup()

    def test_produce_consume(self):
        self.assertEqual(self.client.produce(b"hello world"), 0)
        self.assertEqual(self.client.produce(b"hello world"), 1)
        rec = self.client.consume(1)
        self.assertEqual(rec.value, b"hello world")
        self.assertEqual(rec.offset, 1)

    def test_consume_missing_is_not_found(self):
        with self.assertRaises(grpc.RpcError) as ctx:
            self.client.consume(99)
        self.assertEqual(ctx.exception.code(), grpc.StatusCode.NOT_FOUND)

    def test_consume_stream(self):
        for i in range(3):
            self.client.produce(f"msg-{i}".encode())
        values = [r.value for r in self.client.consume_stream(0)]
        self.assertEqual(values, [b"msg-0", b"msg-1", b"msg-2"])

    def test_produce_stream(self):
        offsets = list(self.client.produce_stream([b"a", b"b", b"c"]))
        self.assertEqual(offsets, [0, 1, 2])


class TestGrpcDurableLog(unittest.TestCase):
    def test_produce_persists(self):
        with tempfile.TemporaryDirectory() as d:
            log = DurableLog(d)
            server = new_grpc_server(log, addr=None)
            target = _unix_target(d, "grpc")
            server.add_insecure_port(target)
            server.start()
            client = Client(target)
            try:
                self.assertEqual(client.produce(b"persist me"), 0)
                self.assertEqual(client.consume(0).value, b"persist me")
            finally:
                client.close()
                server.stop(grace=0)
                log.close()
            log2 = DurableLog(d)
            try:
                self.assertEqual(log2.read(0).value, b"persist me")
            finally:
                log2.close()


if __name__ == "__main__":
    unittest.main()
