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
)

from .test_common import mk_chain


class TestForkChoice(TestCase):
    def test_fork_choice_long_sparse_chain(self):
        # The longest chain is not dense after the fork
        short_coin, long_coin = Coin(sk=0, value=100), Coin(sk=1, value=100)
        common, long_coin = mk_chain(parent=bytes(32), coin=long_coin, slots=range(50))

        long_chain_sparse_ext, long_coin = mk_chain(
            parent=common[-1].id(), coin=long_coin, slots=range(50, 100, 2)
        )

        short_chain_dense_ext, _ = mk_chain(
            parent=common[-1].id(), coin=short_coin, slots=range(50, 100)
        )

        # add more blocks to the long chain to ensure the long chain is indeed longer
        long_chain_further_ext, _ = mk_chain(
            parent=long_chain_sparse_ext[-1].id(), coin=long_coin, slots=range(100, 126)
        )

        long_chain = deepcopy(common) + long_chain_sparse_ext + long_chain_further_ext
        short_chain = deepcopy(common) + short_chain_dense_ext
        assert len(long_chain) > len(short_chain)

        # by setting a low k we trigger the density choice rule
        k = 1
        s = 50

        short_chain = Chain(short_chain, genesis=bytes(32))
        long_chain = Chain(long_chain, genesis=bytes(32))
        assert maxvalid_bg(short_chain, [long_chain], k, s) == short_chain

        # However, if we set k to the fork length, it will be accepted
        k = long_chain.length()
        assert maxvalid_bg(short_chain, [long_chain], k, s) == long_chain

    def test_fork_choice_long_dense_chain(self):
        # The longest chain is also the densest after the fork
        short_coin, long_coin = Coin(sk=0, value=100), Coin(sk=1, value=100)
        common, long_coin = mk_chain(
            parent=bytes(32), coin=long_coin, slots=range(1, 50)
        )

        long_chain_dense_ext, _ = mk_chain(
            parent=common[-1].id(), coin=long_coin, slots=range(50, 100)
        )
        short_chain_sparse_ext, _ = mk_chain(
            parent=common[-1].id(), coin=short_coin, slots=range(50, 100, 2)
        )

        long_chain = deepcopy(common) + long_chain_dense_ext
        short_chain = deepcopy(common) + short_chain_sparse_ext

        k = 1
        s = 50
        short_chain = Chain(short_chain, genesis=bytes(32))
        long_chain = Chain(long_chain, genesis=bytes(32))
        assert maxvalid_bg(short_chain, [long_chain], k, s) == long_chain
