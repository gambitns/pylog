"""Chapter 7 — service discovery: gossip membership in pure Python.

The book embeds HashiCorp Serf: Serf keeps cluster membership with an
efficient, lightweight gossip protocol. Python has no mature Serf
library — that is the honest limit in the handbook (p.3) — so this
module does two things:

1. ``Membership`` — a small, readable gossip implementation of the
   *protocol* Serf uses, so you can read how membership spreads by
   rumour: nodes join, periodically pick a random peer and exchange
   their member lists (push/pull), mark failed members, and converge
   without a central registry. It is a teaching implementation, not a
   production Serf replacement, and it says so.
2. ``SerfAgent`` (``serf.py``) — drives the *real* Serf agent binary
   from Python for the full build, the same agent the book embeds.

The agent (``pylog/internal/agent/agent.py``) uses ``Membership`` by
default and can be pointed at a real Serf agent instead.
"""

import random
import threading
import time
from dataclasses import dataclass, field


@dataclass
class Member:
    id: str
    addr: str  # RPC address, e.g. "127.0.0.1:8401"
    is_leader: bool = False
    alive: bool = True


@dataclass
class _Rumour:
    """One membership change, spread by gossip. ``seen_by`` is the
    dedup set from the course's earlier gossip chunk: a node that has
    already seen a rumour does not spread it again."""
    id: str
    member: Member
    seen_by: set = field(default_factory=set)


class Membership:
    """Gossip membership for one node.

    Every ``gossip_interval`` seconds, pick a random known peer and
    swap member lists (push-pull). A rumour spreads exponentially —
    each round roughly doubles the nodes that know it — and a node
    that stops answering is marked dead after ``suspect_timeout``.
    """

    def __init__(self, self_id: str, self_addr: str,
                 gossip_interval: float = 1.0,
                 suspect_timeout: float = 5.0) -> None:
        self.self_id = self_id
        self._mu = threading.Lock()
        self._members: dict[str, Member] = {
            self_id: Member(id=self_id, addr=self_addr)
        }
        self._rumours: dict[str, _Rumour] = {}
        self._peers: dict[str, "Membership"] = {}  # in-process peers (tests)
        self._gossip_interval = gossip_interval
        self._suspect_timeout = suspect_timeout
        self._last_seen: dict[str, float] = {self_id: time.monotonic()}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # -- local view ----------------------------------------------------
    def members(self) -> list[Member]:
        with self._mu:
            return [m for m in self._members.values() if m.alive]

    def join(self, member: Member) -> None:
        self._receive_rumour(_Rumour(id=f"join:{member.id}", member=member))

    def leave(self, member_id: str) -> None:
        with self._mu:
            if member_id in self._members:
                self._members[member_id].alive = False

    # -- in-process transport (tests / single-process clusters) --------
    def add_peer(self, peer: "Membership") -> None:
        with self._mu:
            self._peers[peer.self_id] = peer

    # -- gossip --------------------------------------------------------
    def start(self) -> None:
        self._thread = threading.Thread(target=self._gossip_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _gossip_loop(self) -> None:
        while not self._stop.wait(self._gossip_interval):
            self._gossip_round()

    def _gossip_round(self) -> None:
        with self._mu:
            peers = list(self._peers.values())
            mine = list(self._members.values())
        if not peers:
            return
        peer = random.choice(peers)
        # Push: send my member list; pull: take theirs back.
        peer._receive_members(mine, sender=self)
        self._receive_members(peer._snapshot(), sender=peer)
        self._mark_suspects()

    def _snapshot(self) -> list[Member]:
        with self._mu:
            return list(self._members.values())

    def _receive_members(self, members: list[Member], sender) -> None:
        for m in members:
            self._receive_rumour(_Rumour(id=f"join:{m.id}", member=m))
        self._last_seen[sender.self_id] = time.monotonic()

    def _receive_rumour(self, rumour: _Rumour) -> None:
        with self._mu:
            if rumour.id in self._rumours and self.self_id in self._rumours[rumour.id].seen_by:
                return  # already seen — do not spread it again
            rumour.seen_by.add(self.self_id)
            self._rumours[rumour.id] = rumour
            self._members[rumour.member.id] = rumour.member
            self._last_seen[rumour.member.id] = time.monotonic()

    def _mark_suspects(self) -> None:
        now = time.monotonic()
        with self._mu:
            for mid, last in list(self._last_seen.items()):
                if mid != self.self_id and now - last > self._suspect_timeout:
                    if mid in self._members:
                        self._members[mid].alive = False
