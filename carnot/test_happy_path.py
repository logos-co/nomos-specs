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

    def test_prepare_vote_for_a_block(self,block:Block, carnot: Carnot) -> Vote:
         vote: Vote = Vote(
            block=block.id(),
            voter=self.id,
            view=self.current_view,
            qc=self.build_qc(votes)
        )
         return vote

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
        #the block, and we can receive blocks with different ids for the same view.
        # There must be only one block per view at most.
        # Maybe we have a dict with view as key and dict[block.id()]block as value?
        block5 = Block(view=4, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block5)


# This  also covers the case when a block has a lower view number than its QC.
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

        # This block should be rejected based on the condition  below in block_is_safe().
        #  block.view >= self.latest_committed_view and block.view == (standard.view + 1)
        # block_is_safe() should return false.
        block5 = Block(view=3, qc=StandardQc(block=block4.id(), view=4))
        carnot.receive_block(block5)

def test_receive_block_has_an_old_qc(self):
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
        block5 = Block(view=5, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block5)




        #Any block  with block.view < 4 must be  committed
 def test_receive_block_and_commit_its_grand_parent_chain(self):
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

        block5 = Block(view=5, qc=StandardQc(block=block3.id(), view=3))
        carnot.receive_block(block5)




# Block3  must be committed as it is the grandparent of block5. Hence, it should not be possible
#to avert it.
 def test_receive_block_has_an_old_qc_and_tries_to_revert_a_committed_block(self):
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

        # 5 This is the old standard qc of block number 2. By using the QC for block2, block5 tries to form a fork
        # to avert block3 and block b4. Block3 is a committed block
        # block_is_safe() should return false.
        block5 = Block(view=5, qc=StandardQc(block=block2.id(), view=2))
        carnot.receive_block(block5)



     # Test cases for  vote:
        #1: If a node votes for a safe block
        #2: If a nodes votes for same block twice
        #3: If a node votes for two different blocks in the same view.
        #4: If a node in parent committee votes before it receives threshold of children's votes
        #5: If a node counts a single vote twice
        #6: If a node votes only for block that are safe
 def test_vote_for_received_block(self):
     carnot = Carnot(int_to_id(0))
     genesis_block = self.add_genesis_block(carnot)
     blocklist=[]
     for i in range(1,5):
        blocklist.append(Block(view=i, qc=StandardQc(block=i - 1, view=i - 1)))







