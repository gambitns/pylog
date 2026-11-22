"""Day 1 — in-memory Log (chat Day 1, book-style rewrite)."""
import unittest

from pylog.internal.server.log import Log, OffsetNotFoundError, Record


class TestMemoryLog(unittest.TestCase):
    def test_append_and_read(self):
        log = Log()
        self.assertEqual(log.append(Record(value=b"Let's Go #1")), 0)
        self.assertEqual(log.append(Record(value=b"Let's Go #2")), 1)
        self.assertEqual(log.read(1).value, b"Let's Go #2")

    def test_read_missing_offset(self):
        log = Log()
        with self.assertRaises(OffsetNotFoundError):
            log.read(9)


if __name__ == "__main__":
    unittest.main()
