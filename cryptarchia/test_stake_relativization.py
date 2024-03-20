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
    def test_inference_on_empty_genesis_epoch(self):
        coin = Coin(sk=0, value=10)
        config = mk_config([coin]).replace(
            initial_inferred_total_stake=20,
            total_stake_learning_rate=0.5,
            active_slot_coeff=0.5,
        )

        genesis = mk_genesis_state([coin])

        node = TestNode(
            config=config,
            leader=Leader(coin=coin, config=config),
            follower=Follower(genesis, config),
        )

        # -- epoch 0 --

        # ..... silence

        # -- epoch 1 --
        # Given no blocks produced in epoch 0,

        epoch1_state = node.epoch_state(Slot(config.epoch_length))

        # given learning rate of 0.5 and 0 occupied slots in epoch 0, we should see inferred total stake drop by half in epoch 1
        assert epoch1_state.inferred_total_stake == 10

        # -- epoch 2 --
        epoch1_state = node.epoch_state(Slot(config.epoch_length * 2))

        # and again, we should see inferred total stake drop by half in epoch 2 given no occupied slots in epoch 1
        assert epoch1_state.inferred_total_stake == 5

    def test_inferred_total_stake_close_to_true_total_stake(self):
        # seed=52, N=10, k=10 - invalid header
        # seed=22, N=3, k=10 - invalid header
        # seed=386, N=2, k=5 - invalid header
        # seed=278, N=2, k=2 - missing parent block
        # seed=543, N=2, k=1 - crash: division by zero

        for seed in range(1000):
            print("Trying seed", seed)
            np.random.seed(seed)

            stake = np.array((np.random.pareto(10, 2) + 1) * 100, dtype=np.int64)
            coins = [Coin(sk=i, value=int(s)) for i, s in enumerate(stake)]

            config = Config.cryptarchia_v0_0_1(stake.sum() * 2).replace(k=1)
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
                for n_idx, node in enumerate(nodes):
                    # shuffle proposed blocks to simulate random delivery
                    block_order = list(range(len(nodes)))
                    np.random.shuffle(block_order)
                    for block_idx in block_order:
                        if block := proposed_blocks[block_idx]:
                            # print(f"{slot}: send {block_idx} -> {n_idx}")
                            node.on_block(block)

            if any(
                slot_leaders.sum() + 1 != len(n.follower.ledger_state) for n in nodes
            ):
                print("Found broken seed", seed)
                print(slot_leaders.sum(), [len(n.follower.ledger_state) for n in nodes])
                break

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
