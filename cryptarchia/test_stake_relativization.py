from unittest import TestCase
from dataclasses import dataclass
import itertools

import numpy as np

from .cryptarchia import (
    Leader,
    Follower,
    BlockHeader,
    Config,
    EpochState,
    LedgerState,
    Coin,
    phi,
    TimeConfig,
    Slot,
)
from .test_common import mk_config, mk_genesis_state

# TODO: tests to implement
# - sim. based test showing inferrer total stake converges to true total stake
# - test that orphans are counted correctly


@dataclass
class TestNode:
    config: Config
    leader: Leader
    follower: Follower

    def epoch_state(self, slot: Slot):
        return self.follower.compute_epoch_state(
            slot.epoch(self.config), self.follower.local_chain
        )

    def on_slot(self, slot: Slot) -> BlockHeader | None:
        parent = self.follower.tip_id()
        epoch_state = self.epoch_state(slot)
        if leader_proof := self.leader.try_prove_slot_leader(epoch_state, slot, parent):
            self.leader.coin = self.leader.coin.evolve()
            return BlockHeader(
                parent=parent,
                slot=slot,
                orphaned_proofs=[],  # TODO
                leader_proof=leader_proof,
                content_size=0,
                content_id=bytes(32),
            )
        return None

    def on_block(self, block: BlockHeader):
        self.follower.on_block(block)


class TestStakeRelativization(TestCase):
    def test_inferred_total_stake_close_to_true_total_stake(self):
        np.random.seed(0)

        config = Config.cryptarchia_v0_0_1().replace(k=10)

        stake = np.array((np.random.pareto(10, 10) + 1) * 100, dtype=np.int64)
        coins = [Coin(sk=i, value=int(s)) for i, s in enumerate(stake)]
        genesis = mk_genesis_state(coins).replace(total_stake=stake.sum() * 2)

        nodes = [
            TestNode(
                config=config,
                leader=Leader(coin=c, config=config),
                follower=Follower(genesis, config),
            )
            for c in coins
        ]

        # Simulate first epoch
        for slot in map(Slot, range(config.epoch_length)):
            proposed_blocks = []
            for node in nodes:
                if block := node.on_slot(slot):
                    proposed_blocks += [block]

            # now deliver the proposed blocks
            for node in nodes:
                # shuffle proposed blocks to simulate random delivery
                np.random.shuffle(proposed_blocks)
                for block in proposed_blocks:
                    node.on_block(block)

        grouped_by_tip = _group_by(nodes, lambda n: n.follower.tip_id())
        for group in grouped_by_tip.values():
            ref_node = group[0]
            ref_epoch_state = ref_node.epoch_state(Slot(config.epoch_length))
            for node in group:
                assert node.epoch_state(Slot(config.epoch_length)) == ref_epoch_state

        representatives = [g[0] for g in grouped_by_tip.values()]

        for node in representatives:
            multiple_of_true_stake = (
                node.epoch_state(Slot(config.epoch_length)).total_stake() / stake.sum()
            )
            assert 0.97 < multiple_of_true_stake < 1, multiple_of_true_stake


def _group_by(iterable, key):
    import itertools

    return {
        k: list(group) for k, group in itertools.groupby(sorted(iterable, key=key), key)
    }
