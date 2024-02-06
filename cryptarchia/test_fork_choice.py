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


def make_block(parent_id: Id, slot: Slot, content: bytes) -> BlockHeader:
    assert len(parent_id) == 32
    content_id = hashlib.sha256(content).digest()
    return BlockHeader(
        parent=parent_id,
        content_size=1,
        slot=slot,
        content_id=content_id,
        leader_proof=MockLeaderProof.from_coin(Coin(sk=0, value=10)),
    )


class TestLeader(TestCase):
    def test_fork_choice_long_sparse_chain(self):
        # The longest chain is not dense after the fork
        common = [make_block(bytes(32), Slot(i), bytes(i)) for i in range(1, 50)]
        long_chain = deepcopy(common)
        short_chain = deepcopy(common)

        for slot in range(50, 100):
            # make arbitrary ids for the different chain so that the blocks appear to be different
            long_content = f"{slot}-long".encode()
            short_content = f"{slot}-short".encode()
            if slot % 2 == 0:
                long_chain.append(make_block(bytes(32), Slot(slot), long_content))
            short_chain.append(make_block(bytes(32), Slot(slot), short_content))
        # add more blocks to the long chain
        for slot in range(100, 200):
            long_content = f"{slot}-long".encode()
            long_chain.append(make_block(bytes(32), Slot(slot), long_content))
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
        common = [make_block(bytes(32), Slot(i), bytes(i)) for i in range(1, 50)]
        long_chain = deepcopy(common)
        short_chain = deepcopy(common)
        for slot in range(50, 100):
            # make arbitrary ids for the different chain so that the blocks appear to be different
            long_content = f"{slot}-long".encode()
            short_content = f"{slot}-short".encode()
            long_chain.append(make_block(bytes(32), Slot(slot), long_content))
            if slot % 2 == 0:
                short_chain.append(make_block(bytes(32), Slot(slot), short_content))
        k = 1
        s = 50
        assert maxvalid_bg(Chain(short_chain), [Chain(long_chain)], k, s) == Chain(
            long_chain
        )
