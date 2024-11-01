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

from .test_common import mk_config, mk_block, mk_genesis_state


class TestLedgerStateUpdate(TestCase):
    def test_on_block_idempotent(self):
        leader_coin = Coin(sk=0, value=100)
        genesis = mk_genesis_state([leader_coin])

        follower = Follower(genesis, mk_config([leader_coin]))

        block = mk_block(slot=0, parent=genesis.block, coin=leader_coin)
        follower.on_block(block)

        # Follower should have accepted the block
        assert follower.tip_state().height == 1
        assert follower.tip() == block

        follower.on_block(block)

        assert follower.tip_state().height == 1
        assert follower.tip() == block
        assert len(follower.ledger_state) == 2
        assert len(follower.forks) == 0

    def test_ledger_state_prevents_coin_reuse(self):
        leader_coin = Coin(sk=0, value=100)
        genesis = mk_genesis_state([leader_coin])

        follower = Follower(genesis, mk_config([leader_coin]))

        block = mk_block(slot=0, parent=genesis.block, coin=leader_coin)
        follower.on_block(block)

        # Follower should have accepted the block
        assert follower.tip_state().height == 1
        assert follower.tip() == block

        # Follower should have updated their ledger state to mark the leader coin as spent
        assert follower.tip_state().verify_unspent(leader_coin.nullifier()) == False

        reuse_coin_block = mk_block(slot=1, parent=block, coin=leader_coin)
        follower.on_block(reuse_coin_block)

        # Follower should *not* have accepted the block
        assert follower.tip_state().height == 1
        assert follower.tip() == block

    def test_ledger_state_is_properly_updated_on_reorg(self):
        coin = [Coin(sk=0, value=100), Coin(sk=1, value=100), Coin(sk=2, value=100)]

        genesis = mk_genesis_state(coin)

        follower = Follower(genesis, mk_config(coin))

        # 1) coin[0] & coin[1] both concurrently win slot 0

        block_1 = mk_block(parent=genesis.block, slot=0, coin=coin[0])
        block_2 = mk_block(parent=genesis.block, slot=0, coin=coin[1])

        # 2) follower sees block 1 first

        follower.on_block(block_1)
        assert follower.tip() == block_1
        assert not follower.tip_state().verify_unspent(coin[0].nullifier())

        # 3) then sees block 2, but sticks with block_1 as the tip

        follower.on_block(block_2)
        assert follower.tip() == block_1
        assert len(follower.forks) == 1, f"{len(follower.forks)}"

        # 4) then coin[2] wins slot 1 and chooses to extend from block_2

        block_3 = mk_block(parent=block_2, slot=1, coin=coin[2])
        follower.on_block(block_3)
        # the follower should have switched over to the block_2 fork
        assert follower.tip() == block_3

        # and the original coin[0] should now be removed from the spent pool
        assert follower.tip_state().verify_unspent(coin[0].nullifier())

    def test_fork_creation(self):
        coins = [Coin(sk=i, value=100) for i in range(7)]
        genesis = mk_genesis_state(coins)

        follower = Follower(genesis, mk_config(coins))

        # coin_0 & coin_1 both concurrently win slot 0 based on the genesis block
        # Both blocks are accepted, and a fork is created "from the genesis block"
        block_1 = mk_block(parent=genesis.block, slot=0, coin=coins[0])
        block_2 = mk_block(parent=genesis.block, slot=0, coin=coins[1])
        follower.on_block(block_1)
        follower.on_block(block_2)
        assert follower.tip() == block_1
        assert len(follower.forks) == 1, f"{len(follower.forks)}"
        assert follower.forks[0] == block_2.id()

        # coin_2 wins slot 1 and chooses to extend from block_1
        # coin_3 also wins slot 1 and but chooses to extend from block_2
        # Both blocks are accepted. Both the local chain and the fork grow. No fork is newly created.
        block_3 = mk_block(parent=block_1, slot=1, coin=coins[2])
        block_4 = mk_block(parent=block_2, slot=1, coin=coins[3])
        follower.on_block(block_3)
        follower.on_block(block_4)
        assert follower.tip() == block_3
        assert len(follower.forks) == 1, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()

        # coin_4 wins slot 1 and but chooses to extend from block_2 as well
        # The block is accepted. A new fork is created "from the block_2".
        block_5 = mk_block(parent=block_2, slot=1, coin=coins[4])
        follower.on_block(block_5)
        assert follower.tip() == block_3
        assert len(follower.forks) == 2, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()
        assert follower.forks[1] == block_5.id()

        # A block based on an unknown parent is not accepted.
        # Nothing changes from the local chain and forks.
        unknown_block = mk_block(parent=block_5, slot=2, coin=coins[5])
        block_6 = mk_block(parent=unknown_block, slot=2, coin=coins[6])
        follower.on_block(block_6)
        assert follower.tip() == block_3
        assert len(follower.forks) == 2, f"{len(follower.forks)}"
        assert follower.forks[0] == block_4.id()
        assert follower.forks[1] == block_5.id()

    def test_epoch_transition(self):
        leader_coins = [Coin(sk=i, value=100) for i in range(4)]
        genesis = mk_genesis_state(leader_coins)
        config = mk_config(leader_coins)

        follower = Follower(genesis, config)

        # We assume an epoch length of 10 slots in this test.
        assert config.epoch_length == 20, f"epoch len: {config.epoch_length}"

        # ---- EPOCH 0 ----

        block_1 = mk_block(slot=0, parent=genesis.block, coin=leader_coins[0])
        follower.on_block(block_1)
        assert follower.tip() == block_1
        assert follower.tip().slot.epoch(config).epoch == 0

        block_2 = mk_block(slot=19, parent=block_1, coin=leader_coins[1])
        follower.on_block(block_2)
        assert follower.tip() == block_2
        assert follower.tip().slot.epoch(config).epoch == 0

        # ---- EPOCH 1 ----

        block_3 = mk_block(slot=20, parent=block_2, coin=leader_coins[2])
        follower.on_block(block_3)
        assert follower.tip() == block_3
        assert follower.tip().slot.epoch(config).epoch == 1

        # ---- EPOCH 2 ----

        # when trying to propose a block for epoch 2, the stake distribution snapshot should be taken
        # at the end of epoch 0, i.e. slot 9
        # To ensure this is the case, we add a new coin just to the state associated with that slot,
        # so that the new block can be accepted only if that is the snapshot used
        # first, verify that if we don't change the state, the block is not accepted
        block_4 = mk_block(slot=40, parent=block_3, coin=Coin(sk=4, value=100))
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

        follower = Follower(genesis, mk_config([coin]))

        # coin wins the first slot
        block_1 = mk_block(slot=0, parent=genesis.block, coin=coin)
        follower.on_block(block_1)
        assert follower.tip() == block_1

        # coin can't be reused to win following slots:
        block_2_reuse = mk_block(slot=1, parent=block_1, coin=coin)
        follower.on_block(block_2_reuse)
        assert follower.tip() == block_1

        # but the evolved coin is eligible
        block_2_evolve = mk_block(slot=1, parent=block_1, coin=coin.evolve())
        follower.on_block(block_2_evolve)
        assert follower.tip() == block_2_evolve

    def test_new_coins_becoming_eligible_after_stake_distribution_stabilizes(self):
        coin = Coin(sk=0, value=100)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        follower = Follower(genesis, config)

        # We assume an epoch length of 20 slots in this test.
        assert config.epoch_length == 20

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
        block_0_1_attempt = mk_block(slot=1, parent=block_0_0, coin=coin_new)
        follower.on_block(block_0_1_attempt)
        assert follower.tip() == block_0_0

        # whereas the evolved coin from genesis can be spent immediately
        block_0_1 = mk_block(slot=1, parent=block_0_0, coin=coin.evolve())
        follower.on_block(block_0_1)
        assert follower.tip() == block_0_1

        # ---- EPOCH 1 ----

        # The newly minted coin is still not eligible in the following epoch since the
        # stake distribution snapshot is taken at the beginning of the previous epoch

        block_1_0 = mk_block(slot=20, parent=block_0_1, coin=coin_new)
        follower.on_block(block_1_0)
        assert follower.tip() == block_0_1

        # ---- EPOCH 2 ----

        # The coin is finally eligible 2 epochs after it was first minted

        block_2_0 = mk_block(slot=40, parent=block_0_1, coin=coin_new)
        follower.on_block(block_2_0)
        assert follower.tip() == block_2_0

        # And now the minted coin can freely use the evolved coin for subsequent blocks
        block_2_1 = mk_block(slot=40, parent=block_2_0, coin=coin_new.evolve())
        follower.on_block(block_2_1)
        assert follower.tip() == block_2_1

    def test_orphaned_proofs(self):
        coin, coin_orphan = Coin(sk=0, value=100), Coin(sk=1, value=100)
        genesis = mk_genesis_state([coin, coin_orphan])

        follower = Follower(genesis, mk_config([coin, coin_orphan]))

        block_0_0 = mk_block(slot=0, parent=genesis.block, coin=coin)
        follower.on_block(block_0_0)
        assert follower.tip() == block_0_0

        coin_new = coin.evolve()
        coin_new_new = coin_new.evolve()
        block_0_1 = mk_block(slot=1, parent=block_0_0, coin=coin_new_new)
        follower.on_block(block_0_1)
        # the coin evolved twice should not be accepted as it is not in the lead commitments
        assert follower.tip() == block_0_0

        # An orphaned proof will not be accepted until a node first sees the corresponding block.
        #
        # Also, notice that the block is using the evolved orphan coin which is not present on the main
        # branch. The evolved orphan commitment is added from the orphan prior to validating the block
        # header as part of orphan importing process
        orphan = mk_block(parent=genesis.block, slot=0, coin=coin_orphan)
        block_0_1 = mk_block(
            slot=1,
            parent=block_0_0,
            coin=coin_orphan.evolve(),
            orphaned_proofs=[orphan],
        )
        follower.on_block(block_0_1)

        # since follower had not seen this orphan prior to being included as
        # an orphan proof, it will be rejected
        assert follower.tip() == block_0_0

        # but all is fine if the follower first sees the orphan block, and then
        # is imported into the main chain
        follower.on_block(orphan)
        follower.on_block(block_0_1)
        assert follower.tip() == block_0_1
