from unittest import TestCase

import numpy as np

from .cryptarchia import (
    Follower,
    TimeConfig,
    BlockHeader,
    Config,
    Coin,
    LedgerState,
    MockLeaderProof,
    Slot,
    Id,
)

from .test_common import mk_config, mk_block


def mk_genesis_state(initial_stake_distribution: list[Coin]) -> LedgerState:
    return LedgerState(
        block=bytes(32),
        nonce=bytes(32),
        total_stake=sum(c.value for c in initial_stake_distribution),
        commitments_spend={c.commitment() for c in initial_stake_distribution},
        commitments_lead={c.commitment() for c in initial_stake_distribution},
        nullifiers=set(),
    )


class TestLedgerStateUpdate(TestCase):
    def test_ledger_state_prevents_coin_reuse(self):
        leader_coin = Coin(sk=0, value=100)
        genesis = mk_genesis_state([leader_coin])

        follower = Follower(genesis, mk_config())

        block = mk_block(slot=0, parent=genesis.block, coin=leader_coin)
        follower.on_block(block)

        # Follower should have accepted the block
        assert follower.local_chain.length() == 1
        assert follower.tip() == block

        # Follower should have updated their ledger state to mark the leader coin as spent
        assert follower.tip_state().verify_unspent(leader_coin.nullifier()) == False

        reuse_coin_block = mk_block(slot=1, parent=block.id(), coin=leader_coin)
        follower.on_block(block)

        # Follower should *not* have accepted the block
        assert follower.local_chain.length() == 1
        assert follower.tip() == block

    def test_ledger_state_is_properly_updated_on_reorg(self):
        coin_1 = Coin(sk=0, value=100)
        coin_2 = Coin(sk=1, value=100)
        coin_3 = Coin(sk=2, value=100)

        genesis = mk_genesis_state([coin_1, coin_2, coin_3])

        follower = Follower(genesis, mk_config())

        # 1) coin_1 & coin_2 both concurrently win slot 0

        block_1 = mk_block(parent=genesis.block, slot=0, coin=coin_1)
        block_2 = mk_block(parent=genesis.block, slot=0, coin=coin_2)

        # 2) follower sees block 1 first

        follower.on_block(block_1)
        assert follower.tip() == block_1
        assert not follower.tip_state().verify_unspent(coin_1.nullifier())

        # 3) then sees block 2, but sticks with block_1 as the tip

        follower.on_block(block_2)
        assert follower.tip() == block_1
        assert len(follower.forks) == 1, f"{len(follower.forks)}"

        # 4) then coin_3 wins slot 1 and chooses to extend from block_2

        block_3 = mk_block(parent=block_2.id(), slot=1, coin=coin_3)
        follower.on_block(block_3)
        # the follower should have switched over to the block_2 fork
        assert follower.tip() == block_3

        # and the original coin_1 should now be removed from the spent pool
        assert follower.tip_state().verify_unspent(coin_1.nullifier())

    def test_epoch_transition(self):
        leader_coins = [Coin(sk=i, value=100) for i in range(4)]
        genesis = mk_genesis_state(leader_coins)
        config = mk_config()

        follower = Follower(genesis, config)

        # We assume an epoch length of 10 slots in this test.
        assert config.epoch_length == 10, f"epoch len: {config.epoch_length}"

        # ---- EPOCH 0 ----

        block_1 = mk_block(slot=0, parent=genesis.block, coin=leader_coins[0])
        follower.on_block(block_1)
        assert follower.tip() == block_1
        assert follower.tip().slot.epoch(config).epoch == 0

        block_2 = mk_block(slot=9, parent=block_1.id(), coin=leader_coins[1])
        follower.on_block(block_2)
        assert follower.tip() == block_2
        assert follower.tip().slot.epoch(config).epoch == 0

        # ---- EPOCH 1 ----

        block_3 = mk_block(slot=10, parent=block_2.id(), coin=leader_coins[2])
        follower.on_block(block_3)
        assert follower.tip() == block_3
        assert follower.tip().slot.epoch(config).epoch == 1

        # ---- EPOCH 2 ----

        # when trying to propose a block for epoch 2, the stake distribution snapshot should be taken
        # at the end of epoch 0, i.e. slot 9
        # To ensure this is the case, we add a new coin just to the state associated with that slot,
        # so that the new block can be accepted only if that is the snapshot used
        # first, verify that if we don't change the state, the block is not accepted
        block_4 = mk_block(slot=20, parent=block_3.id(), coin=Coin(sk=4, value=100))
        follower.on_block(block_4)
        assert follower.tip() == block_3
        # then we add the coin to "spendable commitments" associated with slot 9
        follower.ledger_state[block_2.id()].commitments_spend.add(
            Coin(sk=4, value=100).commitment()
        )
        follower.on_block(block_4)
        assert follower.tip() == block_4
        assert follower.tip().slot.epoch(config).epoch == 2

    def test_evolved_coin_is_eligible_for_leadership(self):
        coin = Coin(sk=0, value=100)

        genesis = mk_genesis_state([coin])

        follower = Follower(genesis, mk_config())

        # coin wins the first slot
        block_1 = mk_block(slot=0, parent=genesis.block, coin=coin)
        follower.on_block(block_1)
        assert follower.tip() == block_1

        # coin can't be reused to win following slots:
        block_2_reuse = mk_block(slot=1, parent=block_1.id(), coin=coin)
        follower.on_block(block_2_reuse)
        assert follower.tip() == block_1

        # but the evolved coin is eligible
        block_2_evolve = mk_block(slot=1, parent=block_1.id(), coin=coin.evolve())
        follower.on_block(block_2_evolve)
        assert follower.tip() == block_2_evolve

    def test_new_coins_becoming_eligible_after_stake_distribution_stabilizes(self):
        config = mk_config()
        coin = Coin(sk=0, value=100)
        genesis = mk_genesis_state([coin])
        follower = Follower(genesis, config)

        # We assume an epoch length of 10 slots in this test.
        assert config.epoch_length == 10

        # ---- EPOCH 0 ----

        block_0_0 = mk_block(slot=0, parent=genesis.block, coin=coin)
        follower.on_block(block_0_0)
        assert follower.tip() == block_0_0

        # mint a new coin to be used for leader elections in upcoming epochs
        coin_new = Coin(sk=1, value=10)
        follower.ledger_state[block_0_0.id()].commitments_spend.add(
            coin_new.commitment()
        )

        # the new coin is not yet eligible for elections
        block_0_1_attempt = mk_block(slot=1, parent=block_0_0.id(), coin=coin_new)
        follower.on_block(block_0_1_attempt)
        assert follower.tip() == block_0_0

        # whereas the evolved coin from genesis can be spent immediately
        block_0_1 = mk_block(slot=1, parent=block_0_0.id(), coin=coin.evolve())
        follower.on_block(block_0_1)
        assert follower.tip() == block_0_1

        # ---- EPOCH 1 ----

        # The newly minted coin is still not eligible in the following epoch since the
        # stake distribution snapshot is taken at the beginning of the previous epoch

        block_1_0 = mk_block(slot=10, parent=block_0_1.id(), coin=coin_new)
        follower.on_block(block_1_0)
        assert follower.tip() == block_0_1

        # ---- EPOCH 2 ----

        # The coin is finally eligible 2 epochs after it was first minted

        block_2_0 = mk_block(
            slot=20,
            parent=block_0_1.id(),
            coin=coin_new,
        )
        follower.on_block(block_2_0)
        assert follower.tip() == block_2_0

        # And now the minted coin can freely use the evolved coin for subsequent blocks

        block_2_1 = mk_block(slot=20, parent=block_2_0.id(), coin=coin_new.evolve())
        follower.on_block(block_2_1)
        assert follower.tip() == block_2_1

    def test_orphaned_proofs(self):
        coin = Coin(sk=0, value=100)
        genesis = mk_genesis_state([coin])

        follower = Follower(genesis, mk_config())

        block_0_0 = mk_block(slot=0, parent=genesis.block, coin=coin)
        follower.on_block(block_0_0)
        assert follower.tip() == block_0_0

        coin_new = coin.evolve()
        coin_new_new = coin_new.evolve()
        block_0_1 = mk_block(slot=1, parent=block_0_0.id(), coin=coin_new_new)
        follower.on_block(block_0_1)
        # the coin evolved twice should not be accepted as it is not in the lead commitments
        assert follower.tip() == block_0_0

        # an orphaned proof with an evolved coin for the same slot as the original coin
        # should not be accepted as the evolved coin is not in the lead commitments at slot 0
        block_0_1 = mk_block(
            slot=1,
            parent=block_0_0.id(),
            coin=coin_new_new,
            orphaned_proofs=[mk_block(parent=genesis.block, slot=0, coin=coin_new)],
        )
        follower.on_block(block_0_1)
        assert follower.tip() == block_0_0

        # the coin evolved twice should be accepted as the evolved coin is in the lead commitments
        # at slot 1 and processed before that
        block_0_2 = mk_block(
            slot=2,
            parent=block_0_0.id(),
            coin=coin_new_new,
            orphaned_proofs=[mk_block(parent=block_0_0.id(), slot=1, coin=coin_new)],
        )
        follower.on_block(block_0_2)
        assert follower.tip() == block_0_2
