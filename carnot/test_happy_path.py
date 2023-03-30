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

    def test_receive_block_has_old_qc(self):
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

