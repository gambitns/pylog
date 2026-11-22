"""Chapters 7-8 — the agent: the thing that ties it all together.

The book's agent (``internal/agent/agent.go``) is the composition
root: it creates the durable log, the gRPC server, the Serf membership,
and the Raft node, then wires them so each feeds the next:

* On startup it joins the cluster (discovery) and starts Raft.
* When it discovers a new peer, it replicates its log to that peer
  (Chapter 7: consume-stream the log from the peer and append what is
  missing — the book's ``replicate``).
* Writes go through Raft (``propose``) when the node is the leader;
  the FSM applies committed entries to the durable log.
* ``GetServers`` answers from the membership list, marking the Raft
  leader — that is what the Chapter 9 resolver reads.

This agent uses the in-process ``Membership`` gossip and ``Node``
Raft core by default (readable, testable, no external binaries). Pass
a real Serf agent (``discovery.serf.SerfAgent``) to run the full
build. Single-node mode (no peers) behaves exactly like Chapters
1-6: writes go straight to the log.
"""

import threading

from pylog.api.v1 import log_pb2
from pylog.internal.discovery.membership import Membership
from pylog.internal.log import Log as DurableLog
from pylog.internal.raft.fsm import FSM
from pylog.internal.raft.raft import Node
from pylog.internal.server.client import Client
from pylog.internal.server.grpc_server import LogServicer, new_grpc_server


class Agent:
    def __init__(self, node_id: str, data_dir: str, rpc_addr: str,
                 peers: list[str] | None = None,
                 membership: Membership | None = None) -> None:
        self.node_id = node_id
        self.rpc_addr = rpc_addr
        self.peers = peers or []
        self.log = DurableLog(data_dir)
        self.fsm = FSM(self.log)
        self.raft = Node(
            node_id, peers=self.peers,
            apply=lambda entry: self.fsm.apply(entry),
        )
        self.membership = membership or Membership(node_id, rpc_addr)
        self._grpc_server = None
        self._stop = threading.Event()

    # -- lifecycle -------------------------------------------------------
    def start(self) -> None:
        self.membership.start()
        servers = [
            log_pb2.Server(id=self.node_id, rpc_addr=self.rpc_addr,
                           is_leader=False)
        ]
        self._grpc_server = new_grpc_server(
            _AgentLog(self), addr=self.rpc_addr, servers=servers)
        self._grpc_server.start()

    def shutdown(self) -> None:
        self.membership.stop()
        if self._grpc_server is not None:
            self._grpc_server.stop(grace=2)
        self.log.close()

    # -- replication (Chapter 7) -----------------------------------------
    def replicate_from(self, peer_addr: str) -> int:
        """Copy records we are missing from ``peer_addr``: consume
        from our highest offset + 1 and append each record. Returns
        the number of records copied. In a Raft cluster this is only
        the catch-up path — steady-state replication goes through
        Raft — but it is how a new node joins with an empty log."""
        client = Client(peer_addr)
        try:
            start = self.log.highest_offset() + 1
            copied = 0
            for record in client.consume_stream(start):
                self.log.append(record)
                copied += 1
            return copied
        finally:
            client.close()

    def is_leader(self) -> bool:
        from pylog.internal.raft.raft import State
        return self.raft.state == State.LEADER


class _AgentLog:
    """The commit-log surface the gRPC servicer needs, routed through
    Raft when this node is clustered, straight to the log when it is
    alone (single-node mode). ``read`` always reads the durable log."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent

    def append(self, record) -> int:
        agent = self._agent
        if agent.peers and not agent.is_leader():
            raise RuntimeError("not the leader")
        if agent.peers:
            # Raft log indexes are 1-based; durable-log offsets are
            # 0-based, and the FSM appends in index order, so the
            # record's offset is index - 1.
            return agent.raft.propose(record.SerializeToString()) - 1
        return agent.log.append(record)

    def read(self, offset: int):
        return self._agent.log.read(offset)
