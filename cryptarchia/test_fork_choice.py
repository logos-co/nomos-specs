from unittest import TestCase
from itertools import repeat
import numpy as np
import hashlib

from copy import deepcopy
from cryptarchia.cryptarchia import (
    block_weight,
    ghost_maxvalid_bg,
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
    def test_ghost_fork_choice(self):
        # Example from the GHOST paper
        #
        #          2D - 3F - 4C - 5B
        #         /
        #        /    3E
        #       /    /
        #    1B - 2C - 3D - 4B
        #   /   \    \
        # 0      \    3C
        #  \      \
        #   \      2B - 3B
        #    \
        #     1A - 2A - 3A - 4A - 5A - 6A

        coin = Coin(sk=1, value=100)

        b0 = BlockHeader(slot=Slot(0), parent=bytes(32))

        b1A = mk_block(b0, 1, coin, content=b"b1A")
        b2A = mk_block(b1A, 2, coin, content=b"b2A")
        b3A = mk_block(b2A, 3, coin, content=b"b3A")
        b4A = mk_block(b3A, 4, coin, content=b"b4A")
        b5A = mk_block(b4A, 5, coin, content=b"b5A")
        b6A = mk_block(b5A, 6, coin, content=b"b6A")
        b1B = mk_block(b0, 1, coin, content=b"b1B")
        b2B = mk_block(b1B, 2, coin, content=b"b2B")
        b3B = mk_block(b2B, 3, coin, content=b"b3B")
        b2C = mk_block(b1B, 2, coin, content=b"b2C")
        b3C = mk_block(b2C, 3, coin, content=b"b3C")
        b2D = mk_block(b1B, 2, coin, content=b"b2D")
        b3D = mk_block(b2C, 3, coin, content=b"b3D")
        b4B = mk_block(b3D, 4, coin, content=b"b4B")
        b3E = mk_block(b2C, 3, coin, content=b"b3E")
        b3F = mk_block(b2D, 3, coin, content=b"b3F")
        b4C = mk_block(b3F, 4, coin, content=b"b4C")
        b5B = mk_block(b4C, 5, coin, content=b"b5B")

        states = {
            b.id(): LedgerState(block=b)
            for b in [
                b0,
                b1A,
                b2A,
                b3A,
                b4A,
                b5A,
                b6A,
                b1B,
                b2B,
                b3B,
                b4B,
                b5B,
                b2C,
                b3C,
                b4C,
                b2D,
                b3D,
                b3E,
                b3F,
            ]
        }

        assert (d := common_prefix_depth(b5B.id(), b3E.id(), states)) == (4, 2), d

        k = 100
        s = int(3 * k / 0.05)
        tip = ghost_maxvalid_bg(
            b5B.id(), [b3E.id(), b4B.id(), b3C.id(), b3B.id(), b6A.id()], k, s, states
        )
        assert tip == b4B.id()

    def test_block_weight_paper(self):
        # Example from the GHOST paper
        #
        #          2D - 3F - 4C - 5B
        #         /
        #        /    3E
        #       /    /
        #    1B - 2C - 3D - 4B
        #   /   \    \
        # 0      \    3C
        #  \      \
        #   \      2B - 3B
        #    \
        #     1A - 2A - 3A - 4A - 5A - 6A

        coin = Coin(sk=1, value=100)

        b0 = BlockHeader(slot=Slot(0), parent=bytes(32))

        b1A = mk_block(b0, 1, coin, content=b"b1A")
        b2A = mk_block(b1A, 2, coin, content=b"b2A")
        b3A = mk_block(b2A, 3, coin, content=b"b3A")
        b4A = mk_block(b3A, 4, coin, content=b"b4A")
        b5A = mk_block(b4A, 5, coin, content=b"b5A")
        b6A = mk_block(b5A, 6, coin, content=b"b6A")
        b1B = mk_block(b0, 1, coin, content=b"b1B")
        b2B = mk_block(b1B, 2, coin, content=b"b2B")
        b3B = mk_block(b2B, 3, coin, content=b"b3B")
        b2C = mk_block(b1B, 2, coin, content=b"b2C")
        b3C = mk_block(b2C, 3, coin, content=b"b3C")
        b2D = mk_block(b1B, 2, coin, content=b"b2D")
        b3D = mk_block(b2C, 3, coin, content=b"b3D")
        b4B = mk_block(b3D, 4, coin, content=b"b4B")
        b3E = mk_block(b2C, 3, coin, content=b"b3E")
        b3F = mk_block(b2D, 3, coin, content=b"b3F")
        b4C = mk_block(b3F, 4, coin, content=b"b4C")
        b5B = mk_block(b4C, 5, coin, content=b"b5B")

        states = {
            b.id(): LedgerState(block=b)
            for b in [
                b0,
                b1A,
                b2A,
                b3A,
                b4A,
                b5A,
                b6A,
                b1B,
                b2B,
                b3B,
                b4B,
                b5B,
                b2C,
                b3C,
                b4C,
                b2D,
                b3D,
                b3E,
                b3F,
            ]
        }

        weight = block_weight(states)

        expected_weight = {
            b0.id(): 19,
            b1A.id(): 6,
            b2A.id(): 5,
            b3A.id(): 4,
            b4A.id(): 3,
            b5A.id(): 2,
            b6A.id(): 1,
            b1B.id(): 12,
            b2B.id(): 2,
            b3B.id(): 1,
            b4B.id(): 1,
            b5B.id(): 1,
            b2C.id(): 5,
            b3C.id(): 1,
            b4C.id(): 2,
            b2D.id(): 4,
            b3D.id(): 2,
            b3E.id(): 1,
            b3F.id(): 3,
        }

        assert weight == expected_weight

    def test_block_weight(self):
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

        weights = block_weight(states)

        expected_weights = {
            b0.id(): 8,
            b1.id(): 5,
            b2.id(): 4,
            b3.id(): 1,
            b4.id(): 2,
            b5.id(): 1,
            b6.id(): 2,
            b7.id(): 1,
        }

        assert weights == expected_weights, weights

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

        assert (d := common_prefix_depth(b0.id(), b0.id(), states)) == (0, 0), d
        assert (d := common_prefix_depth(b1.id(), b0.id(), states)) == (1, 0), d
        assert (d := common_prefix_depth(b0.id(), b1.id(), states)) == (0, 1), d
        assert (d := common_prefix_depth(b1.id(), b1.id(), states)) == (0, 0), d
        assert (d := common_prefix_depth(b2.id(), b0.id(), states)) == (2, 0), d
        assert (d := common_prefix_depth(b0.id(), b2.id(), states)) == (0, 2), d
        assert (d := common_prefix_depth(b3.id(), b0.id(), states)) == (3, 0), d
        assert (d := common_prefix_depth(b0.id(), b3.id(), states)) == (0, 3), d
        assert (d := common_prefix_depth(b1.id(), b4.id(), states)) == (1, 1), d
        assert (d := common_prefix_depth(b4.id(), b1.id(), states)) == (1, 1), d
        assert (d := common_prefix_depth(b1.id(), b5.id(), states)) == (1, 2), d
        assert (d := common_prefix_depth(b5.id(), b1.id(), states)) == (2, 1), d
        assert (d := common_prefix_depth(b2.id(), b5.id(), states)) == (2, 2), d
        assert (d := common_prefix_depth(b5.id(), b2.id(), states)) == (2, 2), d
        assert (d := common_prefix_depth(b3.id(), b5.id(), states)) == (3, 2), d
        assert (d := common_prefix_depth(b5.id(), b3.id(), states)) == (2, 3), d
        assert (d := common_prefix_depth(b3.id(), b6.id(), states)) == (1, 1), d
        assert (d := common_prefix_depth(b6.id(), b3.id(), states)) == (1, 1), d
        assert (d := common_prefix_depth(b3.id(), b7.id(), states)) == (1, 2), d
        assert (d := common_prefix_depth(b7.id(), b3.id(), states)) == (2, 1), d
        assert (d := common_prefix_depth(b5.id(), b7.id(), states)) == (2, 4), d
        assert (d := common_prefix_depth(b7.id(), b5.id(), states)) == (4, 2), d

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

        states = {b.id(): LedgerState(block=b) for b in short_chain + long_chain}

        assert (
            ghost_maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == short_chain[-1].id()
        )

        # However, if we set k to the fork length, it will be accepted
        k = len(long_chain)
        assert (
            ghost_maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == long_chain[-1].id()
        )

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
        states = {b.id(): LedgerState(block=b) for b in short_chain + long_chain}

        assert (
            ghost_maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == long_chain[-1].id()
        )

    def test_fork_choice_integration(self):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        coins = [c_a, c_b]
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        b1, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()

        follower.on_block(b1)

        assert follower.tip_id() == b1.id()
        assert follower.forks == [], follower.forks

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
        assert len(follower.forks) == 1 and follower.forks[0] == b3.id()

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
        assert len(follower.forks) == 1 and follower.forks[0] == b2.id(), follower.forks
