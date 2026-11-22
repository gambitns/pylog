"""Chapter 8 — the finite-state machine: Raft's log applied to pylog.

In the book, Raft's FSM is the bridge between consensus and storage:
``Apply`` receives a committed log entry (a serialized ``Record``),
appends it to the durable log, and returns the offset. ``Snapshot``
serializes the whole log (via ``Log.reader()``) so a slow follower
can catch up in one go instead of entry by entry; ``Restore`` reads
a snapshot back in.

The FSM is also where the book's ``Log`` gains its ``Apply`` method
shape — writes go *through* Raft, never straight to the log, once
the node is part of a cluster. Single-node mode (Chapters 1-4) keeps
writing directly; the agent switches to ``propose`` once Raft is on.
"""

import io

from pylog.api.v1 import log_pb2
from pylog.internal.log import Log as DurableLog

from .raft import LogEntry


class FSM:
    def __init__(self, log: DurableLog) -> None:
        self.log = log

    def apply(self, entry: LogEntry) -> int:
        """Apply one committed entry. Returns the record's offset."""
        record = log_pb2.Record()
        record.ParseFromString(entry.command)
        return self.log.append(record)

    def snapshot(self) -> bytes:
        """The whole durable log as raw bytes (``Log.reader()``)."""
        return self.log.reader().read()

    def restore(self, data: bytes) -> None:
        """Rebuild the log from a snapshot: read length-prefixed
        records and append them. Used when a follower is too far
        behind for entry-by-entry replication."""
        stream = io.BytesIO(data)
        while True:
            len_bytes = stream.read(8)
            if len(len_bytes) < 8:
                break
            size = int.from_bytes(len_bytes, "big")
            payload = stream.read(size)
            if len(payload) < size:
                break
            record = log_pb2.Record()
            record.ParseFromString(payload)
            self.log.append(record)
