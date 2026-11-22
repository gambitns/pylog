"""Day 3 — Chapter 2: protobuf round-trip (draft day-03-protobuf.md,
verified 2026-11-22: Record("Let's Go #1", 0) serializes to 13 bytes
vs 54 bytes for the Day 2 JSON form).
"""
import unittest

from pylog.api.v1 import log_pb2


class TestRecordProto(unittest.TestCase):
    def test_round_trip(self):
        rec = log_pb2.Record(value=b"Let's Go #1", offset=0)
        back = log_pb2.Record()
        back.ParseFromString(rec.SerializeToString())
        self.assertEqual(back.value, b"Let's Go #1")
        self.assertEqual(back.offset, 0)

    def test_wire_size(self):
        rec = log_pb2.Record(value=b"Let's Go #1", offset=0)
        wire = rec.SerializeToString()
        self.assertEqual(len(wire), 13)
        self.assertEqual(wire, b"\n\x0bLet's Go #1")


if __name__ == "__main__":
    unittest.main()
