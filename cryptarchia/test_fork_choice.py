from unittest import TestCase

import numpy as np
import hashlib

from copy import deepcopy
from cryptarchia.cryptarchia import maxvalid_bg, Chain, BlockHeader, Slot, Id


def make_block(parent_id: Id, slot: Slot, block_id: Id) -> BlockHeader:
    return BlockHeader(parent=parent_id, id=block_id, slot=slot)


class TestLeader(TestCase):
    def test_fork_choice_long_sparse_chain(self):
        # The longest chain is not dense after the fork
        common = [make_block(b"", Slot(i), str(i).encode()) for i in range(1, 50)]
        long_chain = deepcopy(common)
        short_chain = deepcopy(common)

        for slot in range(50, 100):
            # make arbitrary ids for the different chain so that the blocks appear to be different
            long_id = hashlib.sha256(f"{slot}-long".encode()).digest()
            short_id = hashlib.sha256(f"{slot}-short".encode()).digest()
            if slot % 2 == 0:
                long_chain.append(make_block(b"", Slot(slot), long_id))
            short_chain.append(make_block(b"", Slot(slot), short_id))
        # add more blocks to the long chain
        for slot in range(100, 200):
            long_chain.append(make_block(b"", Slot(slot), long_id))
        assert len(long_chain) > len(short_chain)
        # by setting a low k we trigger the density choice rule
        k = 1
        s = 50
        assert maxvalid_bg(Chain(short_chain), [Chain(long_chain)], k, s) == Chain(
            short_chain
        )

        # However, if we set k to the fork length, it will be accepted
        k = len(long_chain)
        assert maxvalid_bg(Chain(short_chain), [Chain(long_chain)], k, s) == Chain(
            long_chain
        )

    def test_fork_choice_long_dense_chain(self):
        # The longest chain is also the densest after the fork
        common = [make_block(b"", Slot(i), str(i).encode()) for i in range(1, 50)]
        long_chain = deepcopy(common)
        short_chain = deepcopy(common)
        for slot in range(50, 100):
            # make arbitrary ids for the different chain so that the blocks appear to be different
            long_id = hashlib.sha256(f"{slot}-long".encode()).digest()
            short_id = hashlib.sha256(f"{slot}-short".encode()).digest()
            long_chain.append(make_block(b"", Slot(slot), long_id))
            if slot % 2 == 0:
                short_chain.append(make_block(b"", Slot(slot), short_id))
        k = 1
        s = 50
        assert maxvalid_bg(Chain(short_chain), [Chain(long_chain)], k, s) == Chain(
            long_chain
        )
