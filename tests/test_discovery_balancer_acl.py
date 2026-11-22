"""Chapter 7 — gossip membership spreads by rumour; Chapter 9 —
pickers and the produce-to-leader / consume-from-followers policy;
Chapter 5 — the ACL authorizer."""
import time
import unittest

from pylog.internal.discovery.membership import Member, Membership
from pylog.internal.loadbalancer.balancer import (
    LeastLoadedPicker, PickFirstPicker, RoundRobinPicker,
)
from pylog.internal.server.auth import authorize


class TestMembership(unittest.TestCase):
    def test_gossip_spreads_join(self):
        a = Membership("a", "127.0.0.1:1")
        b = Membership("b", "127.0.0.1:2")
        a.add_peer(b)
        b.add_peer(a)
        a.join(Member(id="c", addr="127.0.0.1:3"))
        # A few gossip rounds: a tells b about c.
        for _ in range(3):
            a._gossip_round()
            b._gossip_round()
        self.assertIn("c", {m.id for m in b.members()})
        self.assertIn("a", {m.id for m in b.members()})

    def test_leave_marks_dead(self):
        m = Membership("a", "127.0.0.1:1")
        m.join(Member(id="b", addr="127.0.0.1:2"))
        self.assertIn("b", {x.id for x in m.members()})
        m.leave("b")
        self.assertNotIn("b", {x.id for x in m.members()})


class TestPickers(unittest.TestCase):
    def test_round_robin_cycles(self):
        picker = RoundRobinPicker()
        servers = [0, 1, 2]
        picks = [picker.pick(servers, {}) for _ in range(5)]
        self.assertEqual(picks, [0, 1, 2, 0, 1])

    def test_pick_first_always_zero(self):
        self.assertEqual(PickFirstPicker().pick([0, 1], {}), 0)

    def test_least_loaded(self):
        picker = LeastLoadedPicker()
        self.assertEqual(picker.pick([0, 1, 2], {0: 5, 1: 1, 2: 3}), 1)


class TestACL(unittest.TestCase):
    def test_root_can_produce_nobody_cannot(self):
        self.assertTrue(authorize("root", "Produce"))
        self.assertTrue(authorize("root", "Consume"))
        self.assertFalse(authorize("nobody", "Produce"))
        self.assertFalse(authorize("nobody", "Consume"))

    def test_unknown_subject_denied(self):
        self.assertFalse(authorize("mallory", "Produce"))


if __name__ == "__main__":
    unittest.main()
