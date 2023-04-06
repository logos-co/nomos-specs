from .carnot import *
from unittest import TestCase, mock
from unittest.mock import patch


class TestCarnotHappyPath(TestCase):
    @staticmethod
    def add_genesis_block(carnot: Carnot) -> Block:
        genesis_block = Block(view=0, qc=StandardQc(block=b"", view=0), content=frozenset(b""))
        carnot.safe_blocks[genesis_block.id()] = genesis_block
        carnot.committed_blocks[genesis_block.id()] = genesis_block
        return genesis_block

    def test_receive_block(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        block = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block)

    def test_receive_multiple_blocks_for_the_same_view(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)
        self.assertEqual(len(carnot.safe_blocks), 5)
        # next block is duplicated and as it is already processed should be skipped
        block5 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block5)
        self.assertEqual(len(carnot.safe_blocks), 5)
        # next block has a different view but is duplicated and as it is already processed should be skipped
        block5 = Block(view=5, qc=StandardQc(block=block3.id(), view=4), content=frozenset(b"4"))
        carnot.receive_block(block5)
        self.assertEqual(len(carnot.safe_blocks), 5)

    def test_receive_block_has_old_view_number(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)

        self.assertEqual(len(carnot.safe_blocks), 5)
        # This block should be rejected based on the condition below in block_is_safe().
        # block.view >= self.latest_committed_view and block.view == (standard.view + 1)
        # block_is_safe() should return false.
        block5 = Block(view=3, qc=StandardQc(block=block4.id(), view=4), content=frozenset(b"5"))
        self.assertFalse(carnot.block_is_safe(block5))
        carnot.receive_block(block5)
        self.assertEqual(len(carnot.safe_blocks), 5)

    def test_receive_block_has_an_old_qc(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)

        self.assertEqual(len(carnot.safe_blocks), 5)
        # 5 This is the old standard qc of block number 3. For standard QC we must always have qc.view==block.view-1.
        # This block should be rejected based on the condition  below in block_is_safe().
        # block.view >= self.latest_committed_view and block.view == (standard.view + 1)
        # block_is_safe() should return false.
        block5 = Block(view=5, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"5"))
        self.assertFalse(carnot.block_is_safe(block5))
        carnot.receive_block(block5)
        self.assertEqual(len(carnot.safe_blocks), 5)

    def test_receive_block_and_commit_its_grand_parent_chain(self):
        """
        Any block  with block.view < 4 must be  committed
        """
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)

        block5 = Block(view=5, qc=StandardQc(block=block4.id(), view=4), content=frozenset(b"5"))
        carnot.receive_block(block5)

        for block in (block1, block2, block3):
            self.assertIn(block.id(), carnot.committed_blocks)

    def test_receive_block_has_an_old_qc_and_tries_to_revert_a_committed_block(self):
        """
        Block3  must be committed as it is the grandparent of block5. Hence, it should not be possible
        to avert it.
        """
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)

        self.assertEqual(len(carnot.safe_blocks), 5)
        # 5 This is the old standard qc of block number 2. By using the QC for block2, block5 tries to form a fork
        # to avert block3 and block b4. Block3 is a committed block
        # block_is_safe() should return false.
        block5 = Block(view=5, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"5"))
        self.assertFalse(carnot.block_is_safe(block5))
        carnot.receive_block(block5)
        self.assertEqual(len(carnot.safe_blocks), 5)

    def test_receive_block_and_verify_if_latest_committed_block_and_high_qc_is_updated(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2), content=frozenset(b"3"))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3), content=frozenset(b"4"))
        carnot.receive_block(block4)

        self.assertEqual(len(carnot.safe_blocks), 5)
        block5 = Block(view=5, qc=StandardQc(block=block4.id(), view=4), content=frozenset(b"5"))
        carnot.receive_block(block5)
        self.assertEqual(carnot.latest_committed_view, 3)
        self.assertEqual(carnot.local_high_qc.view, 4)

    # Test cases for  vote:
    def test_vote_for_received_block(self):
        """
        1: Votes received should increment highest_voted_view and current_view but should not change
        latest_committed_view and last_timeout_view
        """

        class MockOverlay(Overlay):
            def is_member_of_root_committee(self, _id: Id) -> bool:
                return False

            def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
                return True

            def super_majority_threshold(self, _id: Id) -> int:
                return 10

            def parent_committee(self, _id: Id) -> Optional[Committee]:
                return set()

        carnot = Carnot(int_to_id(0))
        carnot.overlay = MockOverlay()
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)
        votes = set(
            Vote(
                voter=int_to_id(i),
                view=1,
                block=block1.id(),
                qc=StandardQc(block=block1.id(), view=1)
            ) for i in range(10)
        )
        carnot.approve_block(block1, votes)
        self.assertEqual(carnot.highest_voted_view, 1)
        self.assertEqual(carnot.current_view, 1)
        self.assertEqual(carnot.latest_committed_view, 0)
        self.assertEqual(carnot.last_timeout_view, None)

    def test_vote_for_received_block_if_threshold_votes_has_not_reached(self):
        """
        2 If last_voted_view is incremented after calling vote with votes lower than.
        """

        class MockOverlay(Overlay):
            def is_member_of_root_committee(self, _id: Id) -> bool:
                return False

            def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
                return True

            def super_majority_threshold(self, _id: Id) -> int:
                return 10

            def parent_committee(self, _id: Id) -> Optional[Committee]:
                return set()

        carnot = Carnot(int_to_id(0))
        carnot.overlay = MockOverlay()
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        carnot.receive_block(block1)

        votes = set(
            Vote(
                voter=int_to_id(i),
                view=1,
                block=block1.id(),
                qc=StandardQc(block=block1.id(), view=1)
            ) for i in range(3)
        )

        with self.assertRaises((AssertionError, )):
            carnot.approve_block(block1, votes)

        # The test passes as asserting fails in len(votes) == self.overlay.super_majority_threshold(self.id)
        # when number of votes are < 9
        self.assertEqual(carnot.highest_voted_view, 0)
        self.assertEqual(carnot.current_view, 0)

    def test_initial_leader_proposes_and_advance(self):
        class MockOverlay(Overlay):
            def is_leader(self, _id: Id):
                return True

            def is_member_root(self, _id: Id):
                return True

            def is_member_leaf(self, _id: Id):
                return True

            def leader(self, view: View) -> Id:
                return int_to_id(0)

            def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
                return True

            def leader_super_majority_threshold(self, _id: Id) -> int:
                return 10

            def super_majority_threshold(self, _id: Id) -> int:
                return 10

            def parent_committee(self, _id: Id) -> Optional[Committee]:
                return set()

        class MockCarnot(Carnot):
            def __init__(self, id):
                super(MockCarnot, self).__init__(id)
                self.proposed_block = None

            def broadcast(self, block):
                self.proposed_block = block

        carnot = MockCarnot(int_to_id(0))
        carnot.overlay = MockOverlay()
        genesis_block = self.add_genesis_block(carnot)

        # votes for genesis block
        votes = set(
            Vote(
                block=genesis_block.id(),
                view=0,
                voter=int_to_id(i),
                qc=StandardQc(
                    block=genesis_block.id(),
                    view=0
                ),
            ) for i in range(10)
        )
        # propose a new block
        carnot.propose_block(view=1, quorum=votes)
        proposed_block = carnot.proposed_block
        # process the proposed block as member of a committee
        carnot.receive_block(proposed_block)
        child_votes = set(
            Vote(
                block=proposed_block.id(),
                view=1,
                voter=int_to_id(i),
                qc=StandardQc(
                    block=genesis_block.id(),
                    view=0
                ),
            ) for i in range(10)
        )
        # vote with votes from child committee
        carnot.approve_block(proposed_block, child_votes)
        # check carnot state advanced
        self.assertTrue(carnot.current_view, 1)
        self.assertEqual(carnot.highest_voted_view, 1)
        self.assertEqual(carnot.local_high_qc.view, 0)
        self.assertIn(proposed_block.id(), carnot.safe_blocks)

    def test_leaf_member_advance(self):
        """
        Leaf committees do not collect votes as they don't have any child. Therefore, leaf committees in happy
        path votes and updates state after receipt of a block
        """
        class MockOverlay(Overlay):
            def is_leader(self, _id: Id):
                return False

            def leader(self, view: View) -> Id:
                return int_to_id(0)

            def parent_committee(self, _id: Id) -> Optional[Committee]:
                return set()

            def is_member_of_leaf_committee(self, _id: Id) -> bool:
                return True

            def super_majority_threshold(self, _id: Id) -> int:
                return 0

        carnot = Carnot(int_to_id(0))
        carnot.overlay = MockOverlay()
        genesis_block = self.add_genesis_block(carnot)
        proposed_block = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0), content=frozenset(b"1"))
        # Receive the proposed block as a member of the leaf committee
        carnot.receive_block(proposed_block)
        carnot.approve_block(proposed_block, set())
        proposed_block = Block(view=2, qc=StandardQc(block=genesis_block.id(), view=1), content=frozenset(b"2"))
        carnot.receive_block(proposed_block)
        carnot.approve_block(proposed_block, set())
        # Assert that the current view, highest voted view, and local high QC have all been updated correctly
        self.assertEqual(carnot.current_view, 2)
        self.assertEqual(carnot.highest_voted_view, 2)
        self.assertEqual(carnot.local_high_qc.view, 1)

        # Assert that the proposed block has been added to the set of safe blocks
        self.assertIn(proposed_block.id(), carnot.safe_blocks)

    def test_single_committee_advance(self):
        """
        Test that having a single committee (both root and leaf) and a leader is able to advance
        """
        class MockCarnot(Carnot):
            def __init__(self, id):
                super(MockCarnot, self).__init__(id)
                self.proposed_block = None
                self.latest_vote = None

            def broadcast(self, block):
                self.proposed_block = block

            def send(self, vote: Vote | Timeout | TimeoutQc, *ids: Id):
                self.latest_vote = vote

        nodes = [MockCarnot(int_to_id(i)) for i in range(4)]
        leader = nodes[0]

        class MockOverlay(Overlay):
            def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
                return False

            def leader_super_majority_threshold(self, _id: Id) -> int:
                return 3

            def is_leader(self, _id: Id):
                # Leader is the node with id 0, otherwise not
                return {
                    int_to_id(0): True
                }.get(_id, False)

            def is_member_of_root_committee(self, _id: Id):
                return True

            def leader(self, view: View) -> Id:
                return int_to_id(0)

            def parent_committee(self, _id: Id) -> Optional[Committee]:
                return None

            def is_member_of_leaf_committee(self, _id: Id) -> bool:
                return True

            def super_majority_threshold(self, _id: Id) -> int:
                return 0

        overlay = MockOverlay()

        # inject overlay
        genesis_block = None
        for node in nodes:
            node.overlay = overlay
            genesis_block = self.add_genesis_block(node)

        # votes for genesis block
        votes = set(
            Vote(
                block=genesis_block.id(),
                view=0,
                voter=int_to_id(i),
                qc=StandardQc(
                    block=genesis_block.id(),
                    view=0
                ),
            ) for i in range(3)
        )
        leader.propose_block(1, votes)
        proposed_block = leader.proposed_block
        votes = []
        for node in nodes:
            node.receive_block(proposed_block)
            node.approve_block(proposed_block, set())
            votes.append(node.latest_vote)
        leader.propose_block(2, set(votes))
        next_proposed_block = leader.proposed_block
        for node in nodes:
            # A node receives the second proposed block
            node.receive_block(next_proposed_block)
            # it hasn't voted for the view 2, so its state is linked to view 1 still
            self.assertEqual(node.highest_voted_view, 1)
            self.assertEqual(node.current_view, 1)
            # when the node approves the vote we update the current view
            # and the local high qc, so they need to be increased
            node.approve_block(next_proposed_block, set())
            self.assertEqual(node.current_view, 2)
            self.assertEqual(node.local_high_qc.view, 1)
            self.assertEqual(node.highest_voted_view, 2)