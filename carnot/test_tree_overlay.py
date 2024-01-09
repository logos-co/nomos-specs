from unittest import TestCase

from carnot.tree_overlay import CarnotOverlay, CarnotTree


class TestCarnotTree(TestCase):
    def setUp(self) -> None:
        self.nodes = [int.to_bytes(i, length=32, byteorder="little") for i in range(10)]
        self.tree = CarnotTree(self.nodes, 3)

    def test_parenting(self):
        root = self.tree.inner_committees[0]
        one = self.tree.inner_committees[1]
        two = self.tree.inner_committees[2]
        self.assertIs(self.tree.parent_committee(one), root)
        self.assertIs(self.tree.parent_committee(two), root)

    def test_root_parenting(self):
        root = self.tree.inner_committees[0]
        self.assertIsNone(self.tree.parent_committee(root))

    def test_childs(self):
        root = self.tree.inner_committees[0]
        one = self.tree.inner_committees[1]
        two = self.tree.inner_committees[2]
        self.assertEqual(self.tree.child_committees(root), (one, two))


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
        self.assertEqual(self.tree.root_committee(), set([self.nodes[9], *self.nodes[:3]]))

    def test_leaf_committees(self):
        self.assertEqual(self.tree.leaf_committees(), {frozenset(self.nodes[3:6]), frozenset(self.nodes[6:9])})

    def test_super_majority_threshold_for_leaf(self):
        self.assertEqual(self.tree.super_majority_threshold(self.nodes[-2]), 0)

    def test_super_majority_threshold_for_root_member(self):
        self.assertEqual(self.tree.super_majority_threshold(self.nodes[0]), 3)

    def test_leader_super_majority_threshold(self):
        self.assertEqual(self.tree.leader_super_majority_threshold(self.nodes[0]), 7)


