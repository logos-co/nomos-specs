from unittest import TestCase
from itertools import repeat
import numpy as np
import hashlib

from copy import deepcopy
from cryptarchia.cryptarchia import (
    maxvalid_bg,
    Chain,
    BlockHeader,
    Slot,
    Id,
    MockLeaderProof,
    Coin,
    Follower,
    common_prefix_depth,
    LedgerState,
)

from .test_common import mk_chain, mk_config, mk_genesis_state, mk_block


class TestForkChoice(TestCase):
    def test_common_prefix_depth(self):

        #             6 - 7
        #           /
        # 0 - 1 - 2 - 3
        #   \
        #     4 - 5

        coin = Coin(sk=1, value=100)

        b0 = BlockHeader(slot=Slot(0), parent=bytes(32))
        b1 = mk_block(b0, 1, coin)
        b2 = mk_block(b1, 2, coin)
        b3 = mk_block(b2, 3, coin)
        b4 = mk_block(b0, 1, coin, content=b"b4")
        b5 = mk_block(b4, 2, coin)
        b6 = mk_block(b2, 3, coin, content=b"b6")
        b7 = mk_block(b6, 4, coin)

        states = {
            b.id(): LedgerState(block=b) for b in [b0, b1, b2, b3, b4, b5, b6, b7]
        }

        assert (d := common_prefix_depth(b0.id(), b0.id(), states)) == 0, d
        assert (d := common_prefix_depth(b1.id(), b0.id(), states)) == 1, d
        assert (d := common_prefix_depth(b0.id(), b1.id(), states)) == 0, d
        assert (d := common_prefix_depth(b1.id(), b1.id(), states)) == 0, d
        assert (d := common_prefix_depth(b2.id(), b0.id(), states)) == 2, d
        assert (d := common_prefix_depth(b0.id(), b2.id(), states)) == 0, d
        assert (d := common_prefix_depth(b3.id(), b0.id(), states)) == 3, d
        assert (d := common_prefix_depth(b0.id(), b3.id(), states)) == 0, d
        assert (d := common_prefix_depth(b1.id(), b4.id(), states)) == 1, d
        assert (d := common_prefix_depth(b4.id(), b1.id(), states)) == 1, d
        assert (d := common_prefix_depth(b1.id(), b5.id(), states)) == 1, d
        assert (d := common_prefix_depth(b5.id(), b1.id(), states)) == 2, d
        assert (d := common_prefix_depth(b2.id(), b5.id(), states)) == 2, d
        assert (d := common_prefix_depth(b5.id(), b2.id(), states)) == 2, d
        assert (d := common_prefix_depth(b3.id(), b5.id(), states)) == 3, d
        assert (d := common_prefix_depth(b5.id(), b3.id(), states)) == 2, d
        assert (d := common_prefix_depth(b3.id(), b6.id(), states)) == 1, d
        assert (d := common_prefix_depth(b6.id(), b3.id(), states)) == 1, d
        assert (d := common_prefix_depth(b3.id(), b7.id(), states)) == 1, d
        assert (d := common_prefix_depth(b7.id(), b3.id(), states)) == 2, d
        assert (d := common_prefix_depth(b5.id(), b7.id(), states)) == 2, d
        assert (d := common_prefix_depth(b7.id(), b5.id(), states)) == 4, d

    def test_fork_choice_long_sparse_chain(self):
        # The longest chain is not dense after the fork
        genesis = BlockHeader(slot=Slot(0), parent=bytes(32))
        short_coin, long_coin = Coin(sk=0, value=100), Coin(sk=1, value=100)
        common, long_coin = mk_chain(parent=genesis, coin=long_coin, slots=range(50))

        long_chain_sparse_ext, long_coin = mk_chain(
            parent=common[-1], coin=long_coin, slots=range(50, 100, 2)
        )

        short_chain_dense_ext, _ = mk_chain(
            parent=common[-1], coin=short_coin, slots=range(50, 100)
        )

        # add more blocks to the long chain to ensure the long chain is indeed longer
        long_chain_further_ext, _ = mk_chain(
            parent=long_chain_sparse_ext[-1], coin=long_coin, slots=range(100, 126)
        )

        long_chain = deepcopy(common) + long_chain_sparse_ext + long_chain_further_ext
        short_chain = deepcopy(common) + short_chain_dense_ext
        assert len(long_chain) > len(short_chain)

        # by setting a low k we trigger the density choice rule
        k = 1
        s = 50

        short_chain = Chain(short_chain, genesis=bytes(32))
        long_chain = Chain(long_chain, genesis=bytes(32))
        states = {
            b.id(): LedgerState(block=b) for b in short_chain.blocks + long_chain.blocks
        }

        assert maxvalid_bg(short_chain, [long_chain], states, k, s) == short_chain

        # However, if we set k to the fork length, it will be accepted
        k = long_chain.length()
        assert maxvalid_bg(short_chain, [long_chain], states, k, s) == long_chain

    def test_fork_choice_long_dense_chain(self):
        # The longest chain is also the densest after the fork
        short_coin, long_coin = Coin(sk=0, value=100), Coin(sk=1, value=100)
        common, long_coin = mk_chain(
            parent=BlockHeader(slot=Slot(0), parent=bytes(32)),
            coin=long_coin,
            slots=range(1, 50),
        )

        long_chain_dense_ext, _ = mk_chain(
            parent=common[-1], coin=long_coin, slots=range(50, 100)
        )
        short_chain_sparse_ext, _ = mk_chain(
            parent=common[-1], coin=short_coin, slots=range(50, 100, 2)
        )

        long_chain = deepcopy(common) + long_chain_dense_ext
        short_chain = deepcopy(common) + short_chain_sparse_ext

        k = 1
        s = 50
        short_chain = Chain(short_chain, genesis=bytes(32))
        long_chain = Chain(long_chain, genesis=bytes(32))
        states = {
            b.id(): LedgerState(block=b) for b in short_chain.blocks + long_chain.blocks
        }

        assert maxvalid_bg(short_chain, [long_chain], states, k, s) == long_chain

    def test_fork_choice_integration(self):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        coins = [c_a, c_b]
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        b1, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()

        follower.on_block(b1)

        assert follower.tip_id() == b1.id()
        assert follower.forks == []

        # -- then we fork --
        #
        #    b2 == tip
        #   /
        # b1
        #   \
        #    b3
        #

        b2, c_a = mk_block(b1, 2, c_a), c_a.evolve()
        b3, c_b = mk_block(b1, 2, c_b), c_b.evolve()

        follower.on_block(b2)
        follower.on_block(b3)

        assert follower.tip_id() == b2.id()
        assert len(follower.forks) == 1 and follower.forks[0].tip_id() == b3.id()

        # -- extend the fork causing a re-org --
        #
        #    b2
        #   /
        # b1
        #   \
        #    b3 - b4 == tip
        #

        b4, c_b = mk_block(b3, 3, c_b), c_a.evolve()
        follower.on_block(b4)

        assert follower.tip_id() == b4.id()
        assert len(follower.forks) == 1 and follower.forks[0].tip_id() == b2.id()
