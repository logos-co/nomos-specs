from unittest import TestCase

from copy import deepcopy
from cryptarchia.cryptarchia import (
    maxvalid_bg,
    Slot,
    Note,
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

        note = Note(sk=1, value=100)

        b0 = mk_genesis_state([]).block
        b1 = mk_block(b0, 1, note)
        b2 = mk_block(b1, 2, note)
        b3 = mk_block(b2, 3, note)
        b4 = mk_block(b0, 1, note, content=b"b4")
        b5 = mk_block(b4, 2, note)
        b6 = mk_block(b2, 3, note, content=b"b6")
        b7 = mk_block(b6, 4, note)

        states = {
            b.id(): LedgerState(block=b) for b in [b0, b1, b2, b3, b4, b5, b6, b7]
        }

        assert (d := common_prefix_depth(b0.id(), b0.id(), states)) == (
            0,
            [b0],
            0,
            [b0],
        ), d
        assert (d := common_prefix_depth(b1.id(), b0.id(), states)) == (
            1,
            [b0, b1],
            0,
            [b0],
        ), d
        assert (d := common_prefix_depth(b0.id(), b1.id(), states)) == (
            0,
            [b0],
            1,
            [b0, b1],
        ), d
        assert (d := common_prefix_depth(b1.id(), b1.id(), states)) == (
            0,
            [b1],
            0,
            [b1],
        ), d
        assert (d := common_prefix_depth(b2.id(), b0.id(), states)) == (
            2,
            [b0, b1, b2],
            0,
            [b0],
        ), d
        assert (d := common_prefix_depth(b0.id(), b2.id(), states)) == (
            0,
            [b0],
            2,
            [b0, b1, b2],
        ), d
        assert (d := common_prefix_depth(b3.id(), b0.id(), states)) == (
            3,
            [b0, b1, b2, b3],
            0,
            [b0],
        ), d
        assert (d := common_prefix_depth(b0.id(), b3.id(), states)) == (
            0,
            [b0],
            3,
            [b0, b1, b2, b3],
        ), d
        assert (d := common_prefix_depth(b1.id(), b4.id(), states)) == (
            1,
            [b0, b1],
            1,
            [b0, b4],
        ), d
        assert (d := common_prefix_depth(b4.id(), b1.id(), states)) == (
            1,
            [b0, b4],
            1,
            [b0, b1],
        ), d
        assert (d := common_prefix_depth(b1.id(), b5.id(), states)) == (
            1,
            [b0, b1],
            2,
            [b0, b4, b5],
        ), d
        assert (d := common_prefix_depth(b5.id(), b1.id(), states)) == (
            2,
            [b0, b4, b5],
            1,
            [b0, b1],
        ), d
        assert (d := common_prefix_depth(b2.id(), b5.id(), states)) == (
            2,
            [b0, b1, b2],
            2,
            [b0, b4, b5],
        ), d
        assert (d := common_prefix_depth(b5.id(), b2.id(), states)) == (
            2,
            [b0, b4, b5],
            2,
            [b0, b1, b2],
        ), d
        assert (d := common_prefix_depth(b3.id(), b5.id(), states)) == (
            3,
            [b0, b1, b2, b3],
            2,
            [b0, b4, b5],
        ), d
        assert (d := common_prefix_depth(b5.id(), b3.id(), states)) == (
            2,
            [b0, b4, b5],
            3,
            [b0, b1, b2, b3],
        ), d
        assert (d := common_prefix_depth(b3.id(), b6.id(), states)) == (
            1,
            [b2, b3],
            1,
            [b2, b6],
        ), d
        assert (d := common_prefix_depth(b6.id(), b3.id(), states)) == (
            1,
            [b2, b6],
            1,
            [b2, b3],
        ), d
        assert (d := common_prefix_depth(b3.id(), b7.id(), states)) == (
            1,
            [b2, b3],
            2,
            [b2, b6, b7],
        ), d
        assert (d := common_prefix_depth(b7.id(), b3.id(), states)) == (
            2,
            [b2, b6, b7],
            1,
            [b2, b3],
        ), d
        assert (d := common_prefix_depth(b5.id(), b7.id(), states)) == (
            2,
            [b0, b4, b5],
            4,
            [b0, b1, b2, b6, b7],
        ), d
        assert (d := common_prefix_depth(b7.id(), b5.id(), states)) == (
            4,
            [b0, b1, b2, b6, b7],
            2,
            [b0, b4, b5],
        ), d

    def test_fork_choice_long_sparse_chain(self):
        # The longest chain is not dense after the fork
        genesis = mk_genesis_state([]).block

        short_note, long_note = Note(sk=0, value=100), Note(sk=1, value=100)
        common, long_note = mk_chain(parent=genesis, note=long_note, slots=range(50))

        long_chain_sparse_ext, long_note = mk_chain(
            parent=common[-1], note=long_note, slots=range(50, 100, 2)
        )

        short_chain_dense_ext, _ = mk_chain(
            parent=common[-1], note=short_note, slots=range(50, 100)
        )

        # add more blocks to the long chain to ensure the long chain is indeed longer
        long_chain_further_ext, _ = mk_chain(
            parent=long_chain_sparse_ext[-1], note=long_note, slots=range(100, 126)
        )

        long_chain = deepcopy(common) + long_chain_sparse_ext + long_chain_further_ext
        short_chain = deepcopy(common) + short_chain_dense_ext
        assert len(long_chain) > len(short_chain)

        # by setting a low k we trigger the density choice rule
        k = 1
        s = 50

        states = {b.id(): LedgerState(block=b) for b in short_chain + long_chain}

        assert (
            maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == short_chain[-1].id()
        )

        # However, if we set k to the fork length, it will be accepted
        k = len(long_chain)
        assert (
            maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == long_chain[-1].id()
        )

    def test_fork_choice_long_dense_chain(self):
        # The longest chain is also the densest after the fork
        short_note, long_note = Note(sk=0, value=100), Note(sk=1, value=100)
        common, long_note = mk_chain(
            parent=mk_genesis_state([]).block,
            note=long_note,
            slots=range(1, 50),
        )

        long_chain_dense_ext, _ = mk_chain(
            parent=common[-1], note=long_note, slots=range(50, 100)
        )
        short_chain_sparse_ext, _ = mk_chain(
            parent=common[-1], note=short_note, slots=range(50, 100, 2)
        )

        long_chain = deepcopy(common) + long_chain_dense_ext
        short_chain = deepcopy(common) + short_chain_sparse_ext

        k = 1
        s = 50
        states = {b.id(): LedgerState(block=b) for b in short_chain + long_chain}

        assert (
            maxvalid_bg(short_chain[-1].id(), [long_chain[-1].id()], k, s, states)
            == long_chain[-1].id()
        )

    def test_fork_choice_integration(self):
        n_a, n_b = Note(sk=0, value=10), Note(sk=1, value=10)
        notes = [n_a, n_b]
        config = mk_config(notes)
        genesis = mk_genesis_state(notes)
        follower = Follower(genesis, config)

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()

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

        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_b = mk_block(b1, 2, n_b), n_b.evolve()

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

        b4, n_b = mk_block(b3, 3, n_b), n_a.evolve()
        follower.on_block(b4)

        assert follower.tip_id() == b4.id()
        assert len(follower.forks) == 1 and follower.forks[0] == b2.id(), follower.forks
