from unittest import TestCase

from cryptarchia.cryptarchia import Note, Follower

from .test_common import mk_config, mk_genesis_state, mk_block


class TestOrphanedProofs(TestCase):
    def test_simple_orphan_import(self):
        n_a, n_b = Note(sk=0, value=10), Note(sk=1, value=10)
        coins = [n_a, n_b]
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        # -- fork --
        #
        #   b2 == tip
        #  /
        # b1
        #  \
        #   b3
        #

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()
        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_b = mk_block(b1, 2, n_b), n_b.evolve()

        for b in [b1, b2, b3]:
            follower.on_block(b)

        assert follower.tip() == b2
        assert [f for f in follower.forks] == [b3.id()]
        assert follower.unimported_orphans() == [b3]

        # -- extend with import --
        #
        #   b2 - b4
        #  /    /
        # b1   /
        #  \  /
        #   b3
        #
        b4, n_a = mk_block(b2, 3, n_a, orphaned_proofs=[b3]), n_a.evolve()
        follower.on_block(b4)

        assert follower.tip() == b4
        assert [f for f in follower.forks] == [b3.id()]
        assert follower.unimported_orphans() == []

    def test_orphan_proof_import_from_long_running_fork(self):
        n_a, n_b = Note(sk=0, value=10), Note(sk=1, value=10)
        coins = [n_a, n_b]
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

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()

        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_a = mk_block(b2, 3, n_a), n_a.evolve()

        b4, n_b = mk_block(b1, 2, n_b), n_b.evolve()
        b5, n_b = mk_block(b4, 3, n_b), n_b.evolve()

        for b in [b1, b2, b3, b4, b5]:
            follower.on_block(b)

        assert follower.tip() == b3
        assert [f for f in follower.forks] == [b5.id()]
        assert follower.unimported_orphans() == [b4, b5]

        # -- extend b3, importing the fork --
        #
        #   b2 - b3 - b6 == tip
        #  /      ___/
        # b1  ___/  /
        #  \ /     /
        #   b4 - b5

        b6, n_a = mk_block(b3, 4, n_a, orphaned_proofs=[b4, b5]), n_a.evolve()
        follower.on_block(b6)

        assert follower.tip() == b6
        assert [f for f in follower.forks] == [b5.id()]

    def test_orphan_proof_import_from_fork_without_direct_shared_parent(self):
        coins = [Note(sk=i, value=10) for i in range(2)]
        n_a, n_b = coins
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

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()

        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_a = mk_block(b2, 3, n_a), n_a.evolve()
        b4, n_a = mk_block(b3, 4, n_a), n_a.evolve()

        b5, n_b = mk_block(b1, 2, n_b), n_b.evolve()
        b6, n_b = mk_block(b5, 3, n_b), n_b.evolve()
        b7, n_b = mk_block(b6, 4, n_b), n_b.evolve()

        for b in [b1, b2, b3, b4, b5, b6, b7]:
            follower.on_block(b)

        assert follower.tip() == b4
        assert [f for f in follower.forks] == [b7.id()]
        assert follower.unimported_orphans() == [b5, b6, b7]

        # -- extend b4, importing the forks --
        #
        #   b2 - b3 - b4 - b8 == tip
        #  /       _______/
        # b1  ____/______/
        #  \ /    /     /
        #   b5 - b6 - b7
        #
        # Earlier implementations of orphan proof validation failed to
        # validate b7 as an orphan here.

        b8, n_a = mk_block(b4, 5, n_a, orphaned_proofs=[b5, b6, b7]), n_a.evolve()
        follower.on_block(b8)

        assert follower.tip() == b8
        assert [f for f in follower.forks] == [b7.id()]
        assert follower.unimported_orphans() == []

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

        coins = [Note(sk=i, value=10) for i in range(3)]
        n_a, n_b, n_c = coins
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()

        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_a = mk_block(b2, 3, n_a), n_a.evolve()

        b4, n_b = mk_block(b1, 2, n_b), n_b.evolve()
        b5, n_b = mk_block(b4, 3, n_b), n_b.evolve()

        b6, n_c = mk_block(b4, 3, n_c), n_c.evolve()

        for b in [b1, b2, b3, b4, b5, b6]:
            follower.on_block(b)

        assert follower.tip() == b3
        assert [f for f in follower.forks] == [b5.id(), b6.id()]
        assert follower.unimported_orphans() == [b4, b5, b6]

        b7, n_a = mk_block(b3, 4, n_a, orphaned_proofs=[b4, b5, b6]), n_a.evolve()

        follower.on_block(b7)
        assert follower.tip() == b7

    def test_transitive_orphan_reimports(self):
        # Two forks, one after the other, with some complicated orphan imports.
        # I don't have different line colors to differentiate orphans from parents
        # so I've added o=XX to differentiate orphans from parents.
        #
        # - The first fork at b3(a) is not too interesting.
        # - The second fork at b4(b) has both b6 and b7 importing b5
        # - crucially b7 uses the evolved commitment from b5
        # - Then finally b8 imports b7.
        #
        # proper orphan proof importing will be able to deal with the fact that
        # b7's commitment was produced outside of the main branch AND the commitment
        # is not part of the current list of orphans in b8
        # (b5 had already been imported, therefore it is not included as an orphan in b8)
        #
        # b1(a) - b2(a) - b3(a) - b4(b) - b6(b, o=b5) - b8(b, o=b7)
        #                    \     \___ __/          __/
        #                     \       _x_         __/
        #                      \     /   \_     /
        #                       -b5(a)-----\-b7(a, o=b5)

        coins = [Note(sk=i, value=10) for i in range(2)]
        n_a, n_b = coins
        config = mk_config(coins)
        genesis = mk_genesis_state(coins)
        follower = Follower(genesis, config)

        b1, n_a = mk_block(genesis.block, 1, n_a), n_a.evolve()
        b2, n_a = mk_block(b1, 2, n_a), n_a.evolve()
        b3, n_a = mk_block(b2, 3, n_a), n_a.evolve()

        b4, n_b = mk_block(b3, 4, n_b), n_b.evolve()
        b5, n_a = mk_block(b3, 4, n_a), n_a.evolve()

        b6, n_b = mk_block(b4, 5, n_b, orphaned_proofs=[b5]), n_b.evolve()
        b7, n_a = mk_block(b4, 5, n_a, orphaned_proofs=[b5]), n_a.evolve()

        b8, n_b = mk_block(b6, 6, n_b, orphaned_proofs=[b7]), n_b.evolve()

        for b in [b1, b2, b3, b4, b5]:
            follower.on_block(b)

        assert follower.tip() == b4
        assert follower.unimported_orphans() == [b5]

        for b in [b6, b7]:
            follower.on_block(b)

        assert follower.tip() == b6
        assert follower.unimported_orphans() == [b7]

        follower.on_block(b8)

        assert follower.tip() == b8
        assert follower.unimported_orphans() == []
