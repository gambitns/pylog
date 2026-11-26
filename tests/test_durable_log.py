"""Chapter 3 — durable log: store/index/segment/log, following the
book's tests (append/read, init-existing, reader, truncate)."""
import os
import tempfile
import unittest

from pylog.api.v1 import log_pb2
from pylog.internal.log import Config, Log, OffsetOutOfRangeError, SegmentConfig
from pylog.internal.log.store import LEN_WIDTH


def _rec(value: bytes) -> log_pb2.Record:
    return log_pb2.Record(value=value)


class TestDurableLog(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_append_read(self):
        log = Log(self.dir, Config(SegmentConfig(max_store_bytes=32, max_index_bytes=1024)))
        self.assertEqual(log.append(_rec(b"hello world")), 0)
        self.assertEqual(log.append(_rec(b"hello world")), 1)
        self.assertEqual(log.read(0).value, b"hello world")
        with self.assertRaises(OffsetOutOfRangeError):
            log.read(9)
        log.close()

    def test_init_existing(self):
        log = Log(self.dir)
        for _ in range(3):
            log.append(_rec(b"hello world"))
        log.close()
        log2 = Log(self.dir)
        self.assertEqual(log2.lowest_offset(), 0)
        self.assertEqual(log2.highest_offset(), 2)
        self.assertEqual(log2.read(2).value, b"hello world")
        log2.close()

    def test_reader(self):
        log = Log(self.dir)
        log.append(_rec(b"hello world"))
        data = log.reader().read()
        read = log_pb2.Record()
        read.ParseFromString(data[LEN_WIDTH:])
        self.assertEqual(read.value, b"hello world")
        log.close()

    def test_truncate(self):
        log = Log(self.dir, Config(SegmentConfig(max_store_bytes=32, max_index_bytes=1024)))
        for _ in range(3):
            log.append(_rec(b"hello world"))
        log.truncate(1)
        with self.assertRaises(OffsetOutOfRangeError):
            log.read(0)
        log.close()

    def test_segment_rollover(self):
        # Tiny segments force a rollover after the first record.
        log = Log(self.dir, Config(SegmentConfig(max_store_bytes=32, max_index_bytes=1024)))
        offsets = [log.append(_rec(b"hello world")) for _ in range(3)]
        self.assertEqual(offsets, [0, 1, 2])
        self.assertEqual(log.read(2).value, b"hello world")
        self.assertTrue(os.path.exists(os.path.join(self.dir, "0.store")))
        log.close()

    def test_read_then_append(self):
        # Regression test (Day 4, 2026-11-25): a read must not move
        # the write position. Append two records, read the first,
        # then append a third — the third must land after the second,
        # not overwrite it. The simplified Day 4 Store (open "r+b",
        # seek + read) failed this; the repo Store is safe because
        # its file is opened "a+b" and reads use os.pread, which
        # does not move a shared file offset.
        log = Log(self.dir)
        self.assertEqual(log.append(_rec(b"hello world")), 0)
        self.assertEqual(log.append(_rec(b"second record")), 1)
        self.assertEqual(log.read(0).value, b"hello world")
        self.assertEqual(log.append(_rec(b"third record")), 2)
        self.assertEqual(log.read(0).value, b"hello world")
        self.assertEqual(log.read(1).value, b"second record")
        self.assertEqual(log.read(2).value, b"third record")
        log.close()


if __name__ == "__main__":
    unittest.main()
