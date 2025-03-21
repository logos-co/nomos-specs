from unittest import TestCase

from .cryptarchia import (
    Note,
    Follower,
    InvalidLeaderProof,
    ParentNotFound,
    iter_chain,
)
from .test_common import mk_block, mk_config, mk_genesis_state


class TestLedgerStateUpdate(TestCase):
    def test_on_block_idempotent(self):
        leader_note = Note(sk=0, value=100)
        genesis = mk_genesis_state([leader_note])

        follower = Follower(genesis, mk_config([leader_note]))

        block = mk_block(slot=0, parent=genesis.block, note=leader_note)
        follower.on_block(block)

        # Follower should have accepted the block
        assert len(list(iter_chain(follower.tip_id(), follower.ledger_state))) == 2
        assert follower.tip() == block

        follower.on_block(block)

        # Should have been a No-op
        assert len(list(iter_chain(follower.tip_id(), follower.ledger_state))) == 2
        assert follower.tip() == block
        assert len(follower.ledger_state) == 2
        assert len(follower.forks) == 0

    def test_ledger_state_allows_note_reuse(self):
        leader_note = Note(sk=0, value=100)
        genesis = mk_genesis_state([leader_note])

        follower = Follower(genesis, mk_config([leader_note]))

        block = mk_block(slot=0, parent=genesis.block, note=leader_note)
        follower.on_block(block)

        # Follower should have accepted the block
        assert len(list(iter_chain(follower.tip_id(), follower.ledger_state))) == 2
        assert follower.tip() == block

        reuse_note_block = mk_block(slot=1, parent=block, note=leader_note)
        follower.on_block(reuse_note_block)

        # Follower should have accepted the block
        assert len(list(iter_chain(follower.tip_id(), follower.ledger_state))) == 3
        assert follower.tip() == reuse_note_block

    def test_ledger_state_is_properly_updated_on_reorg(self):
        note = [Note(sk=0, value=100), Note(sk=1, value=100), Note(sk=2, value=100)]

        genesis = mk_genesis_state(note)

        follower = Follower(genesis, mk_config(note))

        # 1) note[0] & note[1] both concurrently win slot 0

        block_1 = mk_block(parent=genesis.block, slot=0, note=note[0])
        block_2 = mk_block(parent=genesis.block, slot=0, note=note[1])

        # 2) follower sees block 1 first

        follower.on_block(block_1)
        assert follower.tip() == block_1

        # 3) then sees block 2, but sticks with block_1 as the tip

        follower.on_block(block_2)
        assert follower.tip() == block_1
        assert len(follower.forks) == 1, f"{len(follower.forks)}"

        # 4) then note[2] wins slot 1 and chooses to extend from block_2

        block_3 = mk_block(parent=block_2, slot=1, note=note[2])
        follower.on_block(block_3)
        # the follower should have switched over to the block_2 fork
        assert follower.tip() == block_3

    def test_fork_creation(self):
        notes = [Note(sk=i, value=100) for i in range(7)]
        genesis = mk_genesis_state(notes)

        follower = Follower(genesis, mk_config(notes))

        # note_0 & note_1 both concurrently win slot 0 based on the genesis block
        # Both blocks are accepted, and a fork is created "from the genesis block"
        block_1 = mk_block(parent=genesis.block, slot=0, note=notes[0])
        block_2 = mk_block(parent=genesis.block, slot=0, note=notes[1])
        follower.on_block(block_1)
        follower.on_block(block_2)
        assert follower.tip() == block_1
        assert len(follower.forks) == 1, f"{len(follower.forks)}"
        assert follower.forks[0] == block_2.id()

        # note_2 wins slot 1 and chooses to extend from block_1
        # note_3 also wins slot 1 and but chooses to extend from block_2
        # Both blocks are accepted. Both the local chain and the fork grow. No fork is newly created.
        block_3 = mk_block(parent=block_1, slot=1, note=notes[2])
        block_4 = mk_block(parent=block_2, slot=1, note=notes[3])
        follower.on_block(block_3)
        follower.on_block(block_4)
        assert follower.tip() == block_3
        assert len(follower.forks) == 1, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()

        # note_4 wins slot 1 and but chooses to extend from block_2 as well
        # The block is accepted. A new fork is created "from the block_2".
        block_5 = mk_block(parent=block_2, slot=1, note=notes[4])
        follower.on_block(block_5)
        assert follower.tip() == block_3
        assert len(follower.forks) == 2, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()
        assert follower.forks[1] == block_5.id()

        # A block based on an unknown parent is not accepted.
        # Nothing changes from the local chain and forks.
        unknown_block = mk_block(parent=block_5, slot=2, note=notes[5])
        block_6 = mk_block(parent=unknown_block, slot=2, note=notes[6])
        with self.assertRaises(ParentNotFound):
            follower.on_block(block_6)
        assert follower.tip() == block_3
        assert len(follower.forks) == 2, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()
        assert follower.forks[1] == block_5.id()

    def test_epoch_transition(self):
        leader_notes = [Note(sk=i, value=100) for i in range(4)]
        genesis = mk_genesis_state(leader_notes)
        config = mk_config(leader_notes)

        follower = Follower(genesis, config)

        # We assume an epoch length of 10 slots in this test.
        assert config.epoch_length == 20, f"epoch len: {config.epoch_length}"

        # ---- EPOCH 0 ----

        block_1 = mk_block(slot=0, parent=genesis.block, note=leader_notes[0])
        follower.on_block(block_1)
        assert follower.tip() == block_1
        assert follower.tip().slot.epoch(config).epoch == 0

        block_2 = mk_block(slot=19, parent=block_1, note=leader_notes[1])
        follower.on_block(block_2)
        assert follower.tip() == block_2
        assert follower.tip().slot.epoch(config).epoch == 0

        # ---- EPOCH 1 ----

        block_3 = mk_block(slot=20, parent=block_2, note=leader_notes[2])
        follower.on_block(block_3)
        assert follower.tip() == block_3
        assert follower.tip().slot.epoch(config).epoch == 1

        # ---- EPOCH 2 ----

        # when trying to propose a block for epoch 2, the stake distribution snapshot should be taken
        # at the end of epoch 0, i.e. slot 9
        # To ensure this is the case, we add a new note just to the state associated with that slot,
        # so that the new block can be accepted only if that is the snapshot used
        # first, verify that if we don't change the state, the block is not accepted
        block_4 = mk_block(slot=40, parent=block_3, note=Note(sk=4, value=100))
        with self.assertRaises(InvalidLeaderProof):
            follower.on_block(block_4)
        assert follower.tip() == block_3
        # then we add the note to "commitments" associated with slot 9
        follower.ledger_state[block_2.id()].commitments.add(
            Note(sk=4, value=100).commitment()
        )
        follower.on_block(block_4)
        assert follower.tip() == block_4
        assert follower.tip().slot.epoch(config).epoch == 2

    def test_note_added_after_stake_freeze_is_ineligible_for_leadership(self):
        note = Note(sk=0, value=100)

        genesis = mk_genesis_state([note])

        follower = Follower(genesis, mk_config([note]))

        # note wins the first slot
        block_1 = mk_block(slot=0, parent=genesis.block, note=note)
        follower.on_block(block_1)
        assert follower.tip() == block_1

        # note can be reused to win following slots:
        block_2 = mk_block(slot=1, parent=block_1, note=note)
        follower.on_block(block_2)
        assert follower.tip() == block_2

        # but the a new note is ineligible
        note_new = Note(sk=1, value=10)
        follower.tip_state().commitments.add(note_new.commitment())
        block_3_new = mk_block(slot=2, parent=block_2, note=note_new)
        with self.assertRaises(InvalidLeaderProof):
            follower.on_block(block_3_new)

        assert follower.tip() == block_2

    def test_new_notes_becoming_eligible_after_stake_distribution_stabilizes(self):
        note = Note(sk=0, value=100)
        config = mk_config([note])
        genesis = mk_genesis_state([note])
        follower = Follower(genesis, config)

        # We assume an epoch length of 20 slots in this test.
        assert config.epoch_length == 20

        # ---- EPOCH 0 ----

        block_0_0 = mk_block(slot=0, parent=genesis.block, note=note)
        follower.on_block(block_0_0)
        assert follower.tip() == block_0_0

        # mint a new note to be used for leader elections in upcoming epochs
        note_new = Note(sk=1, value=10)
        follower.ledger_state[block_0_0.id()].commitments.add(note_new.commitment())

        # the new note is not yet eligible for elections
        block_0_1_attempt = mk_block(slot=1, parent=block_0_0, note=note_new)
        with self.assertRaises(InvalidLeaderProof):
            follower.on_block(block_0_1_attempt)
        assert follower.tip() == block_0_0

        # ---- EPOCH 1 ----

        # The newly minted note is still not eligible in the following epoch since the
        # stake distribution snapshot is taken at the beginning of the previous epoch

        block_1_0_attempt = mk_block(slot=20, parent=block_0_0, note=note_new)
        with self.assertRaises(InvalidLeaderProof):
            follower.on_block(block_1_0_attempt)
        assert follower.tip() == block_0_0

        # ---- EPOCH 2 ----

        # The note is finally eligible 2 epochs after it was first minted

        block_2_0 = mk_block(slot=40, parent=block_0_0, note=note_new)
        follower.on_block(block_2_0)
        assert follower.tip() == block_2_0
