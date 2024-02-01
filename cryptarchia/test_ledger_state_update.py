from unittest import TestCase

import numpy as np

from .cryptarchia import (
    Follower,
    TimeConfig,
    BlockHeader,
    Config,
    Coin,
    LedgerState,
    MockLeaderProof,
    Slot,
)


def config() -> Config:
    return Config(
        k=10, time=TimeConfig(slots_per_epoch=1000, slot_duration=1, chain_start_time=0)
    )


class TestLedgerStateUpdate(TestCase):
    def test_ledger_state_prevents_coin_reuse(self):
        leader_coin = Coin(pk=0, value=100)
        genesis_state = LedgerState(
            block=bytes(32),
            nonce=bytes(32),
            total_stake=leader_coin.value,
            commitments={leader_coin.commitment()},
            nullifiers=set(),
        )

        follower = Follower(genesis_state, config())

        block = BlockHeader(
            slot=Slot(0),
            parent=genesis_state.block,
            content_size=1,
            content_id=bytes(32),
            leader_proof=MockLeaderProof.from_coin(leader_coin),
        )

        follower.on_block(block)

        # Follower should have accepted the block
        assert follower.local_chain.length() == 1
        assert follower.local_chain.tip() == block

        # Follower should have updated their ledger state to mark the leader coin as spent
        assert follower.ledger_state.verify_unspent(leader_coin.nullifier()) == False

        reuse_coin_block = BlockHeader(
            slot=Slot(0),
            parent=block.id(),
            content_size=1,
            content_id=bytes(32),
            leader_proof=MockLeaderProof(
                commitment=leader_coin.commitment(),
                nullifier=leader_coin.nullifier(),
            ),
        )
        follower.on_block(block)

        # Follower should *not* have accepted the block
        assert follower.local_chain.length() == 1
        assert follower.local_chain.tip() == block
