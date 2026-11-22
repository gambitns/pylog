"""Chapter 8 — Raft core: election, replication, commit, apply."""
import unittest

from pylog.internal.raft.raft import LogEntry, Node, State


def make_cluster(n=3):
    nodes = {}
    ids = [f"node-{i}" for i in range(n)]
    for nid in ids:
        peers = [p for p in ids if p != nid]
        nodes[nid] = Node(nid, peers=peers)
    for node in nodes.values():
        node.attach_cluster(nodes)
    return nodes


class TestRaft(unittest.TestCase):
    def test_election_produces_a_leader(self):
        # One election round: the candidate wins a majority and the
        # other nodes stay followers. (In a live cluster, randomised
        # election timeouts are what stop two nodes winning at once;
        # sequential test rounds would each succeed, so only one
        # node runs an election here.)
        nodes = make_cluster(3)
        leader = nodes["node-0"]
        self.assertTrue(leader.start_election())
        self.assertEqual(leader.state, State.LEADER)
        for nid, node in nodes.items():
            if node is not leader:
                self.assertEqual(node.state, State.FOLLOWER)

    def test_propose_replicates_and_applies(self):
        applied = []
        nodes = make_cluster(3)
        for node in nodes.values():
            node._apply = lambda e, n=node: applied.append((n.id, e.command))
        leader = nodes["node-0"]
        self.assertTrue(leader.start_election())
        idx = leader.propose(b"hello")
        self.assertEqual(idx, 1)
        # Majority holds the entry; the leader commits and applies it.
        self.assertEqual(leader.commit_index, 1)
        self.assertIn((leader.id, b"hello"), applied)
        # Followers received the entry (and the commit on next round).
        leader.heartbeat()
        for node in nodes.values():
            self.assertEqual(len(node.log), 1)
            self.assertEqual(node.log[0].command, b"hello")

    def test_propose_on_follower_raises(self):
        nodes = make_cluster(3)
        leader = nodes["node-0"]
        self.assertTrue(leader.start_election())
        follower = nodes["node-1"]
        with self.assertRaises(RuntimeError):
            follower.propose(b"nope")

    def test_vote_requires_up_to_date_log(self):
        from pylog.internal.raft.raft import RequestVoteRequest
        nodes = make_cluster(2)
        a, b = nodes["node-0"], nodes["node-1"]
        a.log.append(LogEntry(term=1, command=b"x"))
        # b has an empty log and a higher term in the request is not
        # enough: a's log is more up-to-date, so a must not vote for b.
        resp = a.request_vote(RequestVoteRequest(
            term=2, candidate_id="node-1", last_log_index=0, last_log_term=0))
        self.assertFalse(resp.vote_granted)


if __name__ == "__main__":
    unittest.main()
