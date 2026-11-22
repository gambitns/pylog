"""Chapter 9 — client-side discovery and load balancing.

gRPC separates three jobs: *resolvers* discover servers, *pickers*
choose one per call, and *balancers* manage the connections. Python's
grpcio does not expose the Go resolver/picker plugin API, so this
module implements the same three jobs in a small client-side layer
over the generated stubs — the ideas, not the Go API surface:

* ``Resolver`` — polls a known server's ``GetServers`` (Chapter 4/9)
  and keeps the list of servers plus which one is the leader.
* Pickers — three strategies from the book (Day 25):
  - ``PickFirstPicker``: always the first server.
  - ``RoundRobinPicker``: each call to the next server in turn.
  - ``LeastLoadedPicker``: the server with the fewest in-flight calls.
* ``BalancedClient`` — the picker policy the book ends with for a
  single-writer, multiple-reader service: **produce goes to the
  leader** (only the leader can append), **consume is balanced
  across the followers** (so the leader can focus on writes).

Trade-offs, as the book states them: round-robin is fair when every
call costs the same; pick-first is simplest and worst under load;
least-loaded needs honest in-flight counts and is the most work.
"""

import threading

from pylog.internal.server.client import Client


class PickFirstPicker:
    def pick(self, servers: list, in_flight: dict) -> int:
        return 0


class RoundRobinPicker:
    def __init__(self) -> None:
        self._next = 0
        self._mu = threading.Lock()

    def pick(self, servers: list, in_flight: dict) -> int:
        with self._mu:
            idx = self._next % len(servers)
            self._next += 1
            return idx


class LeastLoadedPicker:
    def pick(self, servers: list, in_flight: dict) -> int:
        return min(range(len(servers)), key=lambda i: in_flight.get(i, 0))


class Resolver:
    """Discover servers by asking a seed server for its server list,
    and keep it fresh by re-polling."""

    def __init__(self, seed_addr: str) -> None:
        self._seed_addr = seed_addr
        self._servers: list = []
        self._mu = threading.Lock()

    def refresh(self) -> list:
        client = Client(self._seed_addr)
        try:
            servers = client.get_servers()
        finally:
            client.close()
        with self._mu:
            self._servers = servers
        return servers

    def servers(self) -> list:
        with self._mu:
            return list(self._servers)

    def leader(self):
        with self._mu:
            for s in self._servers:
                if s.is_leader:
                    return s
            return self._servers[0] if self._servers else None


class BalancedClient:
    """Produce to the leader, consume from the followers (round-robin
    by default). One ``Client`` per server, created lazily."""

    def __init__(self, resolver: Resolver, picker=None) -> None:
        self._resolver = resolver
        self._picker = picker or RoundRobinPicker()
        self._clients: dict[str, Client] = {}
        self._in_flight: dict[int, int] = {}
        self._mu = threading.Lock()

    def _client_for(self, addr: str) -> Client:
        with self._mu:
            if addr not in self._clients:
                self._clients[addr] = Client(addr)
            return self._clients[addr]

    def produce(self, value: bytes) -> int:
        leader = self._resolver.leader()
        if leader is None:
            raise RuntimeError("no servers discovered")
        return self._client_for(leader.rpc_addr).produce(value)

    def consume(self, offset: int):
        servers = [s for s in self._resolver.servers() if not s.is_leader]
        if not servers:
            servers = self._resolver.servers()
        if not servers:
            raise RuntimeError("no servers discovered")
        idx = self._picker.pick(servers, self._in_flight)
        return self._client_for(servers[idx].rpc_addr).consume(offset)

    def close(self) -> None:
        with self._mu:
            for client in self._clients.values():
                client.close()
            self._clients.clear()
