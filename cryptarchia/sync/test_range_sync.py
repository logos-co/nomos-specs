from unittest import TestCase

from cryptarchia.cryptarchia import Coin, Follower
from cryptarchia.sync.range_sync import range_sync
from cryptarchia.test_common import mk_block, mk_config, mk_genesis_state


class TestRangeSync(TestCase):
    def test_no_fork(self):
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
        range_sync(new_follower, [follower], genesis.block.slot)
        assert new_follower.tip() == b2
        assert new_follower.forks == []
