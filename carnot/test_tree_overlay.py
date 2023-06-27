from unittest import TestCase

from tree_overlay import CarnotOverlay


class TestTreeOverlay(TestCase):
    def setUp(self) -> None:
        self.nodes = [int.to_bytes(i, length=32, byteorder="little") for i in range(10)]
        self.tree = CarnotOverlay(self.nodes, self.nodes[0], b"0"*32, 3)

    def test_leader(self):
        self.assertEqual(self.tree.leader(), self.nodes[0])

    def test_next_leader_is_advance_current_leader(self):
        leader = self.tree.next_leader()
        self.tree = self.tree.advance(b"1"*32)
        self.assertEqual(leader, self.tree.leader())

    def test_root_committee(self):
        self.assertEqual(self.tree.root_committee(), set(self.nodes[:3]))

    def test_leaf_committees(self):
        self.assertEqual(self.tree.leaf_committees(), {frozenset(self.nodes[3:6]), frozenset(self.nodes[6:])})

    def test_super_majority_threshold_for_leaf(self):
        self.assertEqual(self.tree.super_majority_threshold(self.nodes[-1]), 0)

    def test_super_majority_threshold_for_root_member(self):
        self.assertEqual(self.tree.super_majority_threshold(self.nodes[0]), 3)

    def test_leader_super_majority_threshold(self):
        self.assertEqual(self.tree.leader_super_majority_threshold(self.nodes[-1]), 3)
