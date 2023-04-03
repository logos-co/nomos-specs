from .carnot import *
from unittest import TestCase


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
            def member_of_root_com(self, _id: Id) -> bool:
                return False

            def child_committee(self, parent: Id, child: Id) -> bool:
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
        carnot.vote(block1, votes)
        self.assertEqual(carnot.highest_voted_view, 1)
        self.assertEqual(carnot.current_view, 1)
        self.assertEqual(carnot.latest_committed_view, 0)
        self.assertEqual(carnot.last_timeout_view, None)

    def test_vote_for_received_block_if_threshold_votes_has_not_reached(self):
        """
        2 If last_voted_view is incremented after calling vote with votes lower than.
        """
        class MockOverlay(Overlay):
            def member_of_root_com(self, _id: Id) -> bool:
                return False

            def child_committee(self, parent: Id, child: Id) -> bool:
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
            carnot.vote(block1, votes)

        # The test passes as asserting fails in len(votes) == self.overlay.super_majority_threshold(self.id)
        # when number of votes are < 9
        self.assertEqual(carnot.highest_voted_view, 0)
        self.assertEqual(carnot.current_view, 0)
