from unittest import TestCase

from cryptarchia.cryptarchia import BlockHeader, Coin, Follower
from cryptarchia.sync import InvalidBlockTree, sync
from cryptarchia.test_common import mk_block, mk_config, mk_genesis_state


class TestSync(TestCase):
    def test_sync_single_chain_from_genesis(self):
        # Prepare a peer with a single chain:
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

        # Start a sync from genesis.
        # Result: The same block tree as the peer's.
        local = Follower(genesis, config)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)

    def test_sync_single_chain_from_middle(self):
        # Prepare a peer with a single chain:
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

        # Start a sync from a tree:
        # b0 - b1
        #
        # Result: The same block tree as the peer's.
        local = Follower(genesis, config)
        for b in [b0, b1]:
            peer.on_block(b)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)

    def test_sync_forks_from_genesis(self):
        # Prepare a peer with forks:
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

        # Start a sync from genesis.
        # Result: The same block tree as the peer's.
        local = Follower(genesis, config)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)

    def test_sync_forks_from_middle(self):
        # Prepare a peer with forks:
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

        # Start a sync from a tree:
        # b0 - b1
        #    \
        #      b3
        #
        # Result: The same block tree as the peer's.
        local = Follower(genesis, config)
        for b in [b0, b1, b3]:
            peer.on_block(b)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)

    def test_sync_forks_by_backfilling(self):
        # Prepare a peer with forks:
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

        # Start a sync from a tree without the fork:
        # b0 - b1
        #
        # Result: The same block tree as the peer's.
        local = Follower(genesis, config)
        for b in [b0, b1]:
            peer.on_block(b)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(len(local.ledger_state), len(peer.ledger_state))

    def test_sync_multiple_peers_from_genesis(self):
        # Prepare multiple peers:
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

        # Start a sync from genesis.
        #
        # Result: A merged block tree
        #                b5
        #              /
        # b0 - b1 - b2
        #    \
        #      b3 - b4
        local = Follower(genesis, config)
        sync(local, [peer0, peer1, peer2])
        self.assertEqual(local.tip(), b5)
        self.assertEqual(local.forks, [b4.id()])
        self.assertEqual(len(local.ledger_state), 7)

    def test_reject_invalid_blocks(self):
        # Prepare a peer with invalid blocks:
        # b0 - b1 - b2 - b3 - (invalid_b4) - (invalid_b5)
        #
        # First, build a valid chain (b0 ~ b3):
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

        # And deliberately, add invalid blocks (b4 ~ b5):
        fake_coin = Coin(sk=1, value=10)
        b4, fake_coin = mk_block(b3, 5, fake_coin), fake_coin.evolve()
        b5, fake_coin = mk_block(b4, 6, fake_coin), fake_coin.evolve()
        apply_invalid_block_to_ledger_state(peer, b4)
        apply_invalid_block_to_ledger_state(peer, b5)
        # the tip shouldn't be changed.
        self.assertEqual(peer.tip(), b3)
        self.assertEqual(peer.forks, [])

        # Start a sync from genesis.
        #
        # Result: The same honest chain, but without invalid blocks.
        # b0 - b1 - b2 - b3 == tip
        local = Follower(genesis, config)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)

    def test_reject_invalid_blocks_from_backfilling(self):
        # Prepare a peer with invalid blocks in a fork:
        # b0 - b1 - b3 - b4 - b5 == tip
        #    \
        #      b2 - (invalid_b6) - (invalid_b7)
        #
        # First, build a valid chain (b0 ~ b5):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b3, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b4, c_a = mk_block(b3, 4, c_a), c_a.evolve()
        b5, c_a = mk_block(b4, 5, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # And deliberately, add invalid blocks (b6 ~ b7):
        fake_coin = Coin(sk=2, value=10)
        b6, fake_coin = mk_block(b2, 3, fake_coin), fake_coin.evolve()
        b7, fake_coin = mk_block(b6, 4, fake_coin), fake_coin.evolve()
        apply_invalid_block_to_ledger_state(peer, b6)
        apply_invalid_block_to_ledger_state(peer, b7)
        # the tip shouldn't be changed.
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # Start a sync from a tree:
        # b0 - b1 - b3 - b4
        #
        # Result: The same forks, but without invalid blocks
        # b0 - b1 - b3 - b4 - b5 == tip
        #    \
        #      b2
        local = Follower(genesis, config)
        for b in [b0, b1, b3, b4]:
            peer.on_block(b)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertNotIn(b6.id(), local.ledger_state)
        self.assertNotIn(b7.id(), local.ledger_state)


class TestSyncFromCheckpoint(TestCase):
    def test_sync_single_chain(self):
        # Prepare a peer with a single chain:
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

        # Start a sync from the checkpoint:
        # () - () - b2
        #           ||
        #       checkpoint
        #
        # Result: A honest chain without historical blocks
        # () - () - b2 - b3
        checkpoint = peer.ledger_state[b2.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(
            set(local.ledger_state.keys()), set([genesis.block.id(), b2.id(), b3.id()])
        )

    def test_sync_forks(self):
        # Prepare a peer with forks:
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

        # Start a sync from the checkpoint:
        #       checkpoint
        #           ||
        # () - () - b2
        #
        # Result: Backfilled forks.
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        checkpoint = peer.ledger_state[b2.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertEqual(set(local.ledger_state.keys()), set(peer.ledger_state.keys()))

    def test_sync_from_dishonest_checkpoint(self):
        # Prepare multiple peers and a dishonest checkpoint:
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

        # Start a sync from the dishonest checkpoint:
        #       checkpoint
        #           ||
        # () - () - b4
        #
        # Result: The honest chain is found evetually by backfilling.
        # b0 - b1 - b2 - b5 == tip
        #    \
        #      b3 - b4
        checkpoint = peer1.ledger_state[b4.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        sync(local, [peer0, peer1])
        self.assertEqual(local.tip(), b5)
        self.assertEqual(local.forks, [b4.id()])
        self.assertEqual(len(local.ledger_state.keys()), 7)

    def test_reject_invalid_blocks_from_backfilling_fork(self):
        # Prepare a peer with invalid blocks in a fork:
        # b0 - b1 - b3 - b4 - b5 == tip
        #    \
        #      b2 - (invalid_b6) - (invalid_b7)
        #
        # First, build a valid chain (b0 ~ b5):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b3, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b4, c_a = mk_block(b3, 4, c_a), c_a.evolve()
        b5, c_a = mk_block(b4, 5, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # And deliberately, add invalid blocks (b6 ~ b7):
        fake_coin = Coin(sk=2, value=10)
        b6, fake_coin = mk_block(b2, 3, fake_coin), fake_coin.evolve()
        b7, fake_coin = mk_block(b6, 4, fake_coin), fake_coin.evolve()
        apply_invalid_block_to_ledger_state(peer, b6)
        apply_invalid_block_to_ledger_state(peer, b7)
        # the tip shouldn't be changed.
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # Start a sync from a checkpoint where all anscestors are valid:
        #            checkpoint
        #                ||
        # () - () - () - b4
        #
        # Result: A fork is backfilled, but without invalid blocks.
        # b0 - b1 - b3 - b4 - b5 == tip
        #    \
        #      b2
        checkpoint = peer.ledger_state[b4.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        sync(local, [peer])
        self.assertEqual(local.tip(), peer.tip())
        self.assertEqual(local.forks, peer.forks)
        self.assertNotIn(b6.id(), local.ledger_state)
        self.assertNotIn(b7.id(), local.ledger_state)

    def test_reject_invalid_blocks_from_backfilling_block_tree(self):
        # Prepare a peer with invalid blocks in a fork:
        # b0 - b1 - b3 - b4 - b5 == tip
        #    \
        #      b2 - (invalid_b6) - (invalid_b7)
        #
        # First, build a valid chain (b0 ~ b5):
        c_a, c_b = Coin(sk=0, value=10), Coin(sk=1, value=10)
        config = mk_config([c_a, c_b])
        genesis = mk_genesis_state([c_a, c_b])
        peer = Follower(genesis, config)
        b0, c_a = mk_block(genesis.block, 1, c_a), c_a.evolve()
        b1, c_a = mk_block(b0, 2, c_a), c_a.evolve()
        b2, c_b = mk_block(b0, 2, c_b), c_b.evolve()
        b3, c_a = mk_block(b1, 3, c_a), c_a.evolve()
        b4, c_a = mk_block(b3, 4, c_a), c_a.evolve()
        b5, c_a = mk_block(b4, 5, c_a), c_a.evolve()
        for b in [b0, b1, b2, b3, b4, b5]:
            peer.on_block(b)
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # And deliberately, add invalid blocks (b6 ~ b7):
        fake_coin = Coin(sk=2, value=10)
        b6, fake_coin = mk_block(b2, 3, fake_coin), fake_coin.evolve()
        b7, fake_coin = mk_block(b6, 4, fake_coin), fake_coin.evolve()
        apply_invalid_block_to_ledger_state(peer, b6)
        apply_invalid_block_to_ledger_state(peer, b7)
        # the tip shouldn't be changed.
        self.assertEqual(peer.tip(), b5)
        self.assertEqual(peer.forks, [b2.id()])

        # Start a sync from a checkpoint where some anscestors are invalid:
        # ()          checkpoint
        #   \             ||
        #   () - () - (invalid_b7)
        #
        # Result: `InvalidBlockTree` exception
        checkpoint = peer.ledger_state[b7.id()]
        local = Follower(genesis, config)
        local.apply_checkpoint(checkpoint)
        with self.assertRaises(InvalidBlockTree):
            sync(local, [peer])


def apply_invalid_block_to_ledger_state(follower: Follower, block: BlockHeader):
    state = follower.ledger_state[block.parent].copy()
    state.apply(block)
    follower.ledger_state[block.id()] = state
