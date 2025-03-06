from unittest import TestCase

from cryptarchia.cryptarchia import Coin, Follower
from cryptarchia.sync import sync
from cryptarchia.test_common import mk_block, mk_config, mk_genesis_state


class TestSync(TestCase):
    def test_sync_single_chain_from_genesis(self):
        # b0 - b1 - b2 - b3
        coin = Coin(sk=0, value=10)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        peer = Follower(genesis, config)
        b0, coin = mk_block(genesis.block, 1, coin), coin.evolve()
        b1, coin = mk_block(b0, 2, coin), coin.evolve()
        b2, coin = mk_block(b1, 3, coin), coin.evolve()
        b3, coin = mk_block(b2, 4, coin), coin.evolve()
        for b in [b0, b1, b2, b3]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b3)
        self.assertEqual(peer.forks, [])

        local = Follower(genesis, config)
        self.assertFalse(sync(local, [peer]))
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertTrue(sync(local, [peer]))

    def test_sync_single_chain_from_middle(self):
        # b0 - b1 - b2 - b3
        coin = Coin(sk=0, value=10)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        peer = Follower(genesis, config)
        b0, coin = mk_block(genesis.block, 1, coin), coin.evolve()
        b1, coin = mk_block(b0, 2, coin), coin.evolve()
        b2, coin = mk_block(b1, 3, coin), coin.evolve()
        b3, coin = mk_block(b2, 4, coin), coin.evolve()
        for b in [b0, b1, b2, b3]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b3)
        self.assertEqual(peer.forks, [])

        local = Follower(genesis, config)
        # add until b1
        for b in [b0, b1]:
            peer.on_block(b)
        # start syncing from b1
        self.assertFalse(sync(local, [peer]))
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertTrue(sync(local, [peer]))

    def test_sync_forks_from_genesis(self):
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b4.id()])

        local = Follower(genesis, config)
        self.assertFalse(sync(local, [peer]))
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertTrue(sync(local, [peer]))

    def test_sync_forks_from_middle(self):
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b4.id()])

        # b0 - b1
        #    \
        #      b3
        local = Follower(genesis, config)
        for b in [b0, b1, b3]:
            peer.on_block(b)
        self.assertFalse(sync(local, [peer]))
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertTrue(sync(local, [peer]))

    def test_sync_forks_by_backfilling(self):
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b4.id()])
        self.assertEqual(len(peer.ledger_state), 7)

        # b0 - b1
        local = Follower(genesis, config)
        for b in [b0, b1]:
            peer.on_block(b)
        self.assertFalse(sync(local, [peer]))
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(len(local.ledger_state), len(peer.ledger_state))
        self.assertTrue(sync(local, [peer]))

    def test_sync_multiple_peers_from_genesis(self):
        # Peer-0:                b5
        #                      /
        # Peer-1: b0 - b1 - b2
        #            \
        # Peer-2:      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        peer0 = Follower(genesis, config)
        for b in [b0, b1, b2, b5]:
            peer0.on_block(b)
        self.assertEqual(peer0.tip(), b5)
        self.assertEqual(peer0.forks, [])
        peer1 = Follower(genesis, config)
        for b in [b0, b1, b2]:
            peer1.on_block(b)
        self.assertEqual(peer1.tip(), b2)
        self.assertEqual(peer1.forks, [])
        peer2 = Follower(genesis, config)
        for b in [b0, b3, b4]:
            peer2.on_block(b)
        self.assertEqual(peer2.tip(), b4)
        self.assertEqual(peer2.forks, [])

        local = Follower(genesis, config)
        self.assertFalse(sync(local, [peer0, peer1, peer2]))
        self.assertEqual(local.tip(), b5)
        self.assertEqual(local.forks, [b4.id()])
        self.assertEqual(len(local.ledger_state), 7)
        self.assertTrue(sync(local, [peer0, peer1, peer2]))


class TestSyncFromCheckpoint(TestCase):
    def test_sync_single_chain(self):
        # b0 - b1 - b2 - b3
        #           ||
        #       checkpoint
        coin = Coin(sk=0, value=10)
        config = mk_config([coin])
        genesis = mk_genesis_state([coin])
        peer = Follower(genesis, config)
        b0, coin = mk_block(genesis.block, 1, coin), coin.evolve()
        b1, coin = mk_block(b0, 2, coin), coin.evolve()
        b2, coin = mk_block(b1, 3, coin), coin.evolve()
        b3, coin = mk_block(b2, 4, coin), coin.evolve()
        for b in [b0, b1, b2, b3]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b3)
        self.assertEqual(peer.forks, [])

        # Start from the checkpoint:
        # () - () - b2
        #           ||
        #       checkpoint
        checkpoint = peer.ledger_state[b2.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        self.assertFalse(sync(local, [peer]))
        # Result:
        # () - () - b2 - b3
        #           ||
        #       checkpoint
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(
            set(local.ledger_state.keys()), set([genesis.block.id(), b2.id(), b3.id()])
        )
        self.assertTrue(sync(local, [peer]))

    def test_sync_forks(self):
        #       checkpoint
        #           ||
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b4.id()])

        # Start from the checkpoint:
        #       checkpoint
        #           ||
        # () - () - b2
        checkpoint = peer.ledger_state[b2.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        self.assertFalse(sync(local, [peer]))
        # Result:
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(set(local.ledger_state.keys()), set(peer.ledger_state.keys()))
        self.assertTrue(sync(local, [peer]))

    def test_sync_from_dishonest_checkpoint(self):
        # Peer0: b0 - b1 - b2 - b5 == tip
        #           \
        # Peer1:      b3 - b4
        #                  ||
        #              checkpoint
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b3, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b4, c_b = mk_block(b3, 3, c_b), c_b.evolve()
        b5, c_a = mk_block(b2, 4, c_a), c_a.evolve()
        peer0 = Follower(genesis, config)
        for b in [b0, b1, b2, b5]:
            peer0.on_block(b)
        self.assertEqual(peer0.tip(), b5)
        self.assertEqual(peer0.forks, [])
        peer1 = Follower(genesis, config)
        for b in [b0, b3, b4]:
            peer1.on_block(b)
        self.assertEqual(peer1.tip(), b4)
        self.assertEqual(peer1.forks, [])

        # Start from the checkpoint:
        #       checkpoint
        #           ||
        # () - () - b4
        checkpoint = peer1.ledger_state[b4.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        self.assertFalse(sync(local, [peer0, peer1]))
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        self.assertEqual(local.tip(), b5)
        self.assertEqual(local.forks, [b4.id()])
        self.assertEqual(len(local.ledger_state.keys()), 7)
        self.assertTrue(sync(local, [peer0, peer1]))
