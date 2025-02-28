from copy import deepcopy
from unittest import TestCase

from cryptarchia.cryptarchia import Coin, Follower
from cryptarchia.sync.full_sync import full_sync
from cryptarchia.test_common import mk_block, mk_config, mk_genesis_state


class TestFullSync(TestCase):
    def test_sync_single_chain(self):
        # b0 - b1 - b2
        coin = Coin(sk=0, value=10)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        follower = Follower(genesis, config)
        b0, coin = mk_block(genesis.block, 1, coin), coin.evolve()
        b1, coin = mk_block(b0, 2, coin), coin.evolve()
        b2, coin = mk_block(b1, 3, coin), coin.evolve()
        for b in [b0, b1, b2]:
            follower.on_block(b)
        assert follower.tip() == b2
        assert follower.forks == []

        new_follower = Follower(genesis, config)
        full_sync(new_follower, [follower], genesis.block.slot)
        assert new_follower.tip() == follower.tip()
        assert new_follower.forks == follower.forks

    def test_continue_syncing_single_chain(self):
        # b0 - b1 - b2
        coin = Coin(sk=0, value=10)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        follower = Follower(genesis, config)
        b0, coin = mk_block(genesis.block, 1, coin), coin.evolve()
        b1, coin = mk_block(b0, 2, coin), coin.evolve()
        b2, coin = mk_block(b1, 3, coin), coin.evolve()
        for b in [b0, b1, b2]:
            follower.on_block(b)
        assert follower.tip() == b2
        assert follower.forks == []

        new_follower = deepcopy(follower)

        # follower grows
        # b0 - b1 - b2 - b3 - b4
        b3, coin = mk_block(b2, 4, coin), coin.evolve()
        b4, coin = mk_block(b3, 5, coin), coin.evolve()
        for b in [b3, b4]:
            follower.on_block(b)
        assert follower.tip() == b4

        # new_follower starts syncing from its tip slot
        full_sync(new_follower, [follower], new_follower.tip().slot)
        assert new_follower.tip() == follower.tip()
        assert new_follower.forks == follower.forks

    def test_sync_forks(self):
        # b0 - b1 - b2 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        follower = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        for b in [b0, b1, b2, b3, b4]:
            follower.on_block(b)
        assert follower.tip() == b2
        assert follower.forks == [b4.id()]

        new_follower = Follower(genesis, config)
        full_sync(new_follower, [follower], genesis.block.slot)
        assert new_follower.tip() == follower.tip()
        assert new_follower.forks == follower.forks

    def test_continue_syncing_forks(self):
        # b0 - b1 - b2 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        follower = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        for b in [b0, b1, b2, b3, b4]:
            follower.on_block(b)
        assert follower.tip() == b2
        assert follower.forks == [b4.id()]

        new_follower = deepcopy(follower)

        # all forks grow. the tip is switched.
        # b0 - b1 - b2 - b5
        #    \
        #      b3 - b4 - b6 - b7 == tip
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        b6, c_b = mk_block(b4, 4, c_b), c_b.evolve()
        b7, c_b = mk_block(b6, 5, c_b), c_b.evolve()
        for b in [b5, b6, b7]:
            follower.on_block(b)
        assert follower.tip() == b7
        assert follower.forks == [b5.id()]

        # new_follower starts syncing from its tip slot
        full_sync(new_follower, [follower], new_follower.tip().slot)
        assert new_follower.tip() == follower.tip()
        assert new_follower.forks == follower.forks

    def test_sync_two_different_trees(self):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])

        # Peer 0
        # b0 - b1 - b2
        peer_0 = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        for b in [b0, b1, b2]:
            peer_0.on_block(b)
        assert peer_0.tip() == b2
        assert peer_0.forks == []

        # Peer 1
        # b0 - b3 - b4 - b5
        peer_1 = Follower(genesis, config)
        b0, c_b = mk_block(genesis.block, 1, c_b), c_b.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_b = mk_block(b4, 3, c_b), c_b.evolve()
        for b in [b0, b3, b4, b5]:
            peer_1.on_block(b)
        assert peer_1.tip() == b5
        assert peer_1.forks == []

        # new_follower should have:
        # b0 - b1 - b2
        #    \
        #      b3 - b4 - b5 == tip
        new_follower = Follower(genesis, config)
        full_sync(new_follower, [peer_0, peer_1], genesis.block.slot)
        assert new_follower.tip() == peer_1.tip()
        assert new_follower.forks == [peer_0.tip_id()]

    def test_ignore_blocks_missing_parents(self):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])

        # Peer 0
        # b0 - b1 - b2
        peer_0 = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        for b in [b0, b1, b2]:
            peer_0.on_block(b)
        assert peer_0.tip() == b2
        assert peer_0.forks == []

        # Peer 1
        # b0 - b3 - b4 - b5
        peer_1 = Follower(genesis, config)
        b0, c_b = mk_block(genesis.block, 1, c_b), c_b.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_b = mk_block(b4, 3, c_b), c_b.evolve()
        for b in [b0, b3, b4, b5]:
            peer_1.on_block(b)
        assert peer_1.tip() == b5
        assert peer_1.forks == []

        # new follower syncs the peer 0 first
        new_follower = Follower(genesis, config)
        full_sync(new_follower, [peer_0], genesis.block.slot)
        assert new_follower.tip() == peer_0.tip()
        assert new_follower.forks == peer_0.forks

        # new follower tries to sync the peer 1, but from its tip slot (3).
        # causing all blocks from the peer 1 to be ignored
        # because the peer 1 has a fork different from the peer 0,
        # and the new follower hasn't synced the peer 1 fork until the slot 3.
        full_sync(new_follower, [peer_1], new_follower.tip().slot)
        assert new_follower.tip() == peer_0.tip()
        assert new_follower.forks == peer_0.forks
