from .carnot import *
from unittest import TestCase


class TestCarnotHappyPath(TestCase):
    @staticmethod
    def add_genesis_block(carnot: Carnot) -> Block:
        genesis_block = Block(view=0, qc=StandardQc(block=b"", view=0))
        carnot.safe_blocks[genesis_block.id()] = genesis_block
        carnot.committed_blocks[genesis_block.id()] = genesis_block
        return genesis_block

    def test_receive_block(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        block = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0))
        carnot.receive_block(block)


    def test_receive_multiple_blocks_for_the_same_view(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block4)

        # This test seem to fail  because  safe_block dict checks for id of
        #the block and we can receive blocks with different ids for the same view.
        # There must be only one block per view at most.
        # May be we have a dict with view as key and dict[block.id()]block as value?
        block5 = Block(view=4, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block5)


 def test_receive_block_has_old_view_number(self):
        carnot = Carnot(int_to_id(0))
        genesis_block = self.add_genesis_block(carnot)
        # 1
        block1 = Block(view=1, qc=StandardQc(block=genesis_block.id(), view=0))
        carnot.receive_block(block1)

        # 2
        block2 = Block(view=2, qc=StandardQc(block=block1.id(), view=1))
        carnot.receive_block(block2)

        # 3
        block3 = Block(view=3, qc=StandardQc(block=block2.id(), view=2))
        carnot.receive_block(block3)
        # 4
        block4 = Block(view=4, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block4)

        # 5 This is the old standard qc of block number 3. For standarnd QC we must always have qc.view==block.view-1.
        # This block should be rejected based on the condition  below in block_is_safe().
        #  block.view >= self.latest_committed_view and block.view == (standard.view + 1)
        # block_is_safe() should return false.
        block5 = Block(view=3, qc=StandardQc(block=block4.id(), view=4))
        carnot.receive_block(block5)


