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
            orphans = self.follower.unimported_orphans(parent)
            self.leader.coin = self.leader.coin.evolve()
            block = BlockHeader(
                parent=parent,
                slot=slot,
                orphaned_proofs=orphans,
                leader_proof=leader_proof,
                content_size=0,
                content_id=bytes(32),
            )
            return block
        return None

    def on_block(self, block: BlockHeader):
        self.follower.on_block(block)


class TestStakeRelativization(TestCase):
    def test_inferred_total_stake_close_to_true_total_stake(self):
        np.random.seed(1)

        stake = np.array((np.random.pareto(10, 10) + 1) * 100, dtype=np.int64)
        coins = [Coin(sk=i, value=int(s)) for i, s in enumerate(stake)]

        config = Config.cryptarchia_v0_0_1(stake.sum() * 2).replace(k=30)
        genesis = mk_genesis_state(coins)

        nodes = [
            TestNode(
                config=config,
                leader=Leader(coin=c, config=config),
                follower=Follower(genesis, config),
            )
            for c in coins
        ]

        T = config.epoch_length * 2
        slot_leaders = np.zeros(T, dtype=np.int32)
        for slot in map(Slot, range(T)):
            proposed_blocks = [n.on_slot(slot) for n in nodes]
            slot_leaders[slot.absolute_slot] = len(
                proposed_blocks
            ) - proposed_blocks.count(None)
            # for node in nodes:
            #     if block := node.on_slot(slot):
            #         proposed_blocks += [block]

            # now deliver the proposed blocks
            for node in nodes:
                # shuffle proposed blocks to simulate random delivery
                np.random.shuffle(proposed_blocks)
                for block in proposed_blocks:
                    if block:
                        node.on_block(block)

        grouped_by_tip = _group_by(nodes, lambda n: n.follower.tip_id())
        for group in grouped_by_tip.values():
            ref_node = group[0]
            ref_epoch_state = ref_node.epoch_state(Slot(T))
            for node in group:
                assert node.epoch_state(Slot(T)) == ref_epoch_state

        reps = [g[0] for g in grouped_by_tip.values()]

        print()
        print("T", T)
        print(
            f"lottery stats mean={slot_leaders.mean():.2f} var={slot_leaders.var():.2f}"
        )
        print("true total stake\t", stake.sum())
        print("D_0\t", config.initial_inferred_total_stake)
        print(
            f"D_{Slot(T).epoch(config).epoch}\t",
            [r.epoch_state(Slot(T)).total_stake() for r in reps],
        )
        print("true leader count\t", slot_leaders.sum())
        print(
            "follower leader counts\t",
            [r.follower.tip_state().leader_count for r in reps],
        )

        import pdb

        pdb.set_trace()
        for node in reps:
            multiple_of_true_stake = (
                node.epoch_state(Slot(T)).total_stake() / stake.sum()
            )
            assert 0.97 < multiple_of_true_stake < 1, multiple_of_true_stake


def _group_by(iterable, key):
    import itertools

    return {
        k: list(group) for k, group in itertools.groupby(sorted(iterable, key=key), key)
    }


def run_in_parallel(task, params, workers=12):
    from concurrent.futures.thread import ThreadPoolExecutor

    def driver(pair):
        i, p = pair
        result = task(p)
        return result

    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(driver, enumerate(params)))
    return results
