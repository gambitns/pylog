"""Chapter 8 — Raft consensus: a compact, readable Python core.

The book uses HashiCorp Raft (Go library). There is no drop-in Python
port — the honest limit in the handbook (p.3) — so this module is a
readable implementation of the Raft paper's core, written to be read
in one sitting, and ``fsm.py`` puts the book's state machine over it.
For a running cluster the agent wires this core up in-process; if you
need a battle-tested library instead, ``pysyncobj`` is the maintained
Python option named in the handbook — see ``docs/days/day-22.md`` for
the trade-off, stated plainly rather than hidden.

What is implemented (Raft, Figure 2 of the paper, as in the book):
* Server states: follower, candidate, leader. Terms, voted-for, and
  the election timeout (randomised, so split votes resolve).
* ``RequestVote``: a candidate wins only if its log is at least as
  up-to-date as the voter's (last term, then last index).
* ``AppendEntries``: the leader replicates entries and sends
  heartbeats; a follower rejects entries whose ``prev_log_index`` /
  ``prev_log_term`` don't match, and the leader backs up
  (``next_index``) until they do.
* Leader completeness: an entry is committed once a majority has it;
  only then may the state machine apply it.
* ``apply`` callback: the leader/followers hand committed entries to
  the state machine (``fsm.py``) in log order.

Transport is deliberately in-process (method calls between ``Node``
objects) so the *algorithm* can be tested without networking. The
agent (``agent.py``) is where Raft meets the network: its stream
layer sends the same messages over gRPC. That split — algorithm here,
transport there — is exactly how the book separates Raft from its
stream layer.
"""

import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum


class State(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    term: int
    command: bytes  # a serialized Record (protobuf), as in fsm.py


@dataclass
class RequestVoteRequest:
    term: int
    candidate_id: str
    last_log_index: int
    last_log_term: int


@dataclass
class RequestVoteResponse:
    term: int
    vote_granted: bool


@dataclass
class AppendEntriesRequest:
    term: int
    leader_id: str
    prev_log_index: int
    prev_log_term: int
    entries: list = field(default_factory=list)
    leader_commit: int = 0


@dataclass
class AppendEntriesResponse:
    term: int
    success: bool


class Node:
    def __init__(self, node_id: str, peers: list[str] | None = None,
                 election_timeout: tuple[float, float] = (0.15, 0.30),
                 apply=None) -> None:
        self.id = node_id
        self.peers = peers or []
        self.state = State.FOLLOWER
        self.current_term = 0
        self.voted_for: str | None = None
        self.log: list[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0
        self._mu = threading.Lock()
        self._election_timeout = election_timeout
        self._last_heartbeat = time.monotonic()
        self._apply = apply  # called with LogEntry when committed
        self._votes_received: set[str] = set()
        self._next_index: dict[str, int] = {}
        self._match_index: dict[str, int] = {}
        # In-process transport: id -> Node, filled in by the cluster.
        self._cluster: dict[str, "Node"] = {}

    # -- transport plumbing (tests / agent) -----------------------------
    def attach_cluster(self, cluster: dict[str, "Node"]) -> None:
        self._cluster = cluster

    def _send_request_vote(self, peer_id: str, req: RequestVoteRequest):
        return self._cluster[peer_id].request_vote(req)

    def _send_append_entries(self, peer_id: str, req: AppendEntriesRequest):
        return self._cluster[peer_id].append_entries(req)

    # -- helpers --------------------------------------------------------
    def _last_log_index(self) -> int:
        return len(self.log)

    def _last_log_term(self) -> int:
        return self.log[-1].term if self.log else 0

    def _random_timeout(self) -> float:
        lo, hi = self._election_timeout
        return random.uniform(lo, hi)

    def _majority(self) -> int:
        return (len(self.peers) + 1) // 2 + 1

    # -- RPC handlers ---------------------------------------------------
    def request_vote(self, req: RequestVoteRequest) -> RequestVoteResponse:
        with self._mu:
            if req.term < self.current_term:
                return RequestVoteResponse(self.current_term, False)
            if req.term > self.current_term:
                self.current_term = req.term
                self.state = State.FOLLOWER
                self.voted_for = None
            up_to_date = (
                req.last_log_term > self._last_log_term()
                or (req.last_log_term == self._last_log_term()
                    and req.last_log_index >= self._last_log_index())
            )
            if (self.voted_for is None or self.voted_for == req.candidate_id) and up_to_date:
                self.voted_for = req.candidate_id
                self._last_heartbeat = time.monotonic()
                return RequestVoteResponse(self.current_term, True)
            return RequestVoteResponse(self.current_term, False)

    def append_entries(self, req: AppendEntriesRequest) -> AppendEntriesResponse:
        with self._mu:
            if req.term < self.current_term:
                return AppendEntriesResponse(self.current_term, False)
            if req.term > self.current_term:
                self.current_term = req.term
                self.voted_for = None
            self.state = State.FOLLOWER
            self._last_heartbeat = time.monotonic()
            if req.prev_log_index > 0:
                if req.prev_log_index > len(self.log):
                    return AppendEntriesResponse(self.current_term, False)
                if self.log[req.prev_log_index - 1].term != req.prev_log_term:
                    return AppendEntriesResponse(self.current_term, False)
            # Delete any conflicting entries, then append the new ones.
            idx = req.prev_log_index
            for entry in req.entries:
                if idx < len(self.log):
                    if self.log[idx].term != entry.term:
                        del self.log[idx:]
                        self.log.append(entry)
                else:
                    self.log.append(entry)
                idx += 1
            if req.leader_commit > self.commit_index:
                self.commit_index = min(req.leader_commit, len(self.log))
                self._apply_committed()
            return AppendEntriesResponse(self.current_term, True)

    def _apply_committed(self) -> None:
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied - 1]
            if self._apply is not None:
                self._apply(entry)

    # -- elections ------------------------------------------------------
    def start_election(self) -> bool:
        """Run one election round. Returns True if this node becomes
        leader. Callers (the agent's ticker, or a test) drive timing;
        this method does one round, synchronously."""
        with self._mu:
            self.state = State.CANDIDATE
            self.current_term += 1
            self.voted_for = self.id
            self._votes_received = {self.id}
            term = self.current_term
            req = RequestVoteRequest(
                term=term, candidate_id=self.id,
                last_log_index=self._last_log_index(),
                last_log_term=self._last_log_term(),
            )
        for peer_id in self.peers:
            try:
                resp = self._send_request_vote(peer_id, req)
            except KeyError:
                continue
            with self._mu:
                if resp.term > self.current_term:
                    self.current_term = resp.term
                    self.state = State.FOLLOWER
                    self.voted_for = None
                    return False
                if resp.vote_granted and self.state == State.CANDIDATE:
                    self._votes_received.add(peer_id)
        with self._mu:
            if len(self._votes_received) >= self._majority():
                self._become_leader()
                return True
            return False

    def _become_leader(self) -> None:
        self.state = State.LEADER
        for peer_id in self.peers:
            self._next_index[peer_id] = len(self.log) + 1
            self._match_index[peer_id] = 0

    # -- leader replication ---------------------------------------------
    def propose(self, command: bytes) -> int:
        """Append a command to the leader's log and replicate it.
        Returns the log index. Raises if this node is not the leader."""
        with self._mu:
            if self.state != State.LEADER:
                raise RuntimeError("not the leader")
            self.log.append(LogEntry(term=self.current_term, command=command))
            index = len(self.log)
        self.replicate()
        return index

    def replicate(self) -> None:
        """One replication round: send each follower the entries it
        is missing (backing up ``next_index`` on rejection), then
        advance the commit index once a majority holds an entry."""
        with self._mu:
            if self.state != State.LEADER:
                return
            term = self.current_term
            commit = self.commit_index
        for peer_id in self.peers:
            with self._mu:
                next_idx = self._next_index.get(peer_id, len(self.log) + 1)
                prev_idx = next_idx - 1
                prev_term = self.log[prev_idx - 1].term if prev_idx > 0 else 0
                entries = list(self.log[next_idx - 1:])
            req = AppendEntriesRequest(
                term=term, leader_id=self.id, prev_log_index=prev_idx,
                prev_log_term=prev_term, entries=entries, leader_commit=commit,
            )
            try:
                resp = self._send_append_entries(peer_id, req)
            except KeyError:
                continue
            with self._mu:
                if resp.term > self.current_term:
                    self.current_term = resp.term
                    self.state = State.FOLLOWER
                    self.voted_for = None
                    return
                if resp.success:
                    self._match_index[peer_id] = prev_idx + len(entries)
                    self._next_index[peer_id] = prev_idx + len(entries) + 1
                elif self._next_index.get(peer_id, 1) > 1:
                    self._next_index[peer_id] -= 1
        self._advance_commit()

    def _advance_commit(self) -> None:
        with self._mu:
            if self.state != State.LEADER:
                return
            for n in range(len(self.log), self.commit_index, -1):
                count = 1  # the leader itself
                count += sum(
                    1 for m in self._match_index.values() if m >= n
                )
                if count >= self._majority() and self.log[n - 1].term == self.current_term:
                    self.commit_index = n
                    self._apply_committed()
                    break

    def heartbeat(self) -> None:
        """An empty AppendEntries round — the leader's heartbeat."""
        self.replicate()
