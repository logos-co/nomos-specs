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
)

from .test_common import mk_chain, mk_config, mk_genesis_state, mk_block


class TestOrphanedProofs(TestCase):
    def test_orphan_proof_import_from_long_running_fork(self):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        coins = [c_a, c_b]
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        # -- fork --
        #
        #   b2 - b3 == tip
        #  /
        # b1
        #  \
        #   b4 - b5
        #

        b1, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()

        b2, c_a = mk_block(b1.id(), 2, c_a), c_a.evolve()
        b3, c_a = mk_block(b2.id(), 3, c_a), c_a.evolve()

        b4, c_b = mk_block(b1.id(), 2, c_b), c_b.evolve()
        b5, c_b = mk_block(b4.id(), 3, c_b), c_b.evolve()

        for b in [b1, b2, b3, b4, b5]:
            follower.on_block(b)

        assert follower.tip_id() == b3.id()
        assert len(follower.forks) == 1 and follower.forks[0].tip_id() == b5.id()
        assert follower.unimported_orphans(follower.tip_id()) == [b4, b5]

        # -- extend b3, importing the fork --
        #
        #   b2 - b3 - b6 == tip
        #  /      ___/
        # b1  ___/  /
        #  \ /     /
        #   b4 - b5

        import pdb

        pdb.set_trace()

        b6, c_a = mk_block(b3.id(), 4, c_a, orphaned_proofs=[b4, b5]), c_a.evolve()
        follower.on_block(b6)

        assert follower.tip_id() == b6.id()
        assert len(follower.forks) == 1 and follower.forks[0].tip_id() == b5.id()

    def test_orphan_proof_import_from_fork_of_fork(self):
        coins = [Coin(sk=i, value=10) for i in range(2)]
        c_a, c_b = coins
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        # -- forks --
        #
        #   b2 - b3 - b4 == tip
        #  /
        # b1
        #  \
        #   b5 - b6 - b7

        b1, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()

        b2, c_a = mk_block(b1.id(), 2, c_a), c_a.evolve()
        b3, c_a = mk_block(b2.id(), 3, c_a), c_a.evolve()
        b4, c_a = mk_block(b3.id(), 4, c_a), c_a.evolve()

        b5, c_b = mk_block(b1.id(), 2, c_b), c_b.evolve()
        b6, c_b = mk_block(b5.id(), 3, c_b), c_b.evolve()
        b7, c_b = mk_block(b6.id(), 4, c_b), c_b.evolve()

        for b in [b1, b2, b3, b4, b5, b6, b7]:
            follower.on_block(b)

        assert follower.tip_id() == b4.id()
        assert [f.tip_id() for f in follower.forks] == [b7.id()]
        assert follower.unimported_orphans(follower.tip_id()) == [b5, b6, b7]

        # -- extend b4, importing the forks --
        #
        #   b2 - b3 - b4 - b8 == tip
        #  /       _______/
        # b1  ____/______/
        #  \ /    /     /
        #   b5 - b6 - b7

        b8, c_a = mk_block(b4.id(), 5, c_a, orphaned_proofs=[b5, b6, b7]), c_a.evolve()
        follower.on_block(b8)

        assert follower.tip_id() == b8.id()
        assert [f.tip_id() for f in follower.forks] == [b7.id()]
        assert follower.unimported_orphans(follower.tip_id()) == []

    def test_unimported_orphans(self):
        # Given the following fork graph:
        #
        #   b2 - b3
        #  /
        # b1
        #  \
        #   b4 - b5
        #    \
        #     -- b6
        #
        # Orphans w.r.t. to b3 are b4..6, thus extending from b3 with b7 would
        # give the following fork graph
        #
        #   b2 - b3 --- b7== tip
        #  /       ____/
        # b1  ____/ __/
        #  \ /     / /
        #   b4 - b5 /
        #    \     /
        #     -- b6
        #

        coins = [Coin(sk=i, value=10) for i in range(3)]
        c_a, c_b, c_c = coins
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        b1, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()

        b2, c_a = mk_block(b1.id(), 2, c_a), c_a.evolve()
        b3, c_a = mk_block(b2.id(), 3, c_a), c_a.evolve()

        b4, c_b = mk_block(b1.id(), 2, c_b), c_b.evolve()
        b5, c_b = mk_block(b4.id(), 3, c_b), c_b.evolve()

        b6, c_c = mk_block(b4.id(), 3, c_c), c_c.evolve()

        for b in [b1, b2, b3, b4, b5, b6]:
            follower.on_block(b)

        assert follower.tip() == b3
        assert [f.tip() for f in follower.forks] == [b5, b6]

        import pdb

        pdb.set_trace()
        assert follower.unimported_orphans(follower.tip_id()) == [b4, b5, b6]

        b7, c_a = mk_block(b3.id(), 4, c_a, orphaned_proofs=[b4, b5, b6]), c_a.evolve()

        follower.on_block(b7)
        assert follower.tip() == b7
