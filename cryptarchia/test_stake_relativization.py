from unittest import TestCase
from dataclasses import dataclass
import itertools

import numpy as np

from .cryptarchia import Config, Coin, Slot
from .test_common import mk_config, mk_genesis_state, mk_block, TestNode, Follower


class TestStakeRelativization(TestCase):
    def test_ledger_leader_counting(self):
        coins = [Coin(sk=i, value=10) for i in range(2)]
        c_a, c_b = coins

        config = mk_config(coins)
        genesis = mk_genesis_state(coins)

        follower = Follower(genesis, config)

        # initially, there are 0 leaders
        assert follower.tip_state().leader_count == 0

        # after a block, 1 leader has been observed
        b1 = mk_block(genesis.block, slot=1, coin=c_a)
        follower.on_block(b1)
        assert follower.tip_state().leader_count == 1

        # on fork, tip state is not updated
        orphan = mk_block(genesis.block, slot=1, coin=c_b)
        follower.on_block(orphan)
        assert follower.tip_state().block == b1.id()
        assert follower.tip_state().leader_count == 1

        # after orphan is adopted, leader count should jumpy by 2 (each orphan counts as a leader)
        b2 = mk_block(b1.id(), slot=2, coin=c_a.evolve(), orphaned_proofs=[orphan])
        follower.on_block(b2)
        assert follower.tip_state().block == b2.id()
        assert follower.tip_state().leader_count == 3

    def test_inference_on_empty_genesis_epoch(self):
        coin = Coin(sk=0, value=10)
        config = mk_config([coin]).replace(
            initial_total_active_stake=20,
            total_active_stake_learning_rate=0.5,
            active_slot_coeff=0.5,
        )
        genesis = mk_genesis_state([coin])
        node = TestNode(config, genesis, coin)

        # -- epoch 0 --

        # ..... silence

        # -- epoch 1 --
        # Given no blocks produced in epoch 0,

        epoch1_state = node.epoch_state(Slot(config.epoch_length))

        # given learning rate of 0.5 and 0 occupied slots in epoch 0, we should see
        # inferred total stake drop by half in epoch 1
        assert epoch1_state.inferred_total_active_stake == 10

        # -- epoch 2 --
        epoch1_state = node.epoch_state(Slot(config.epoch_length * 2))

        # and again, we should see inferred total stake drop by half in epoch 2 given
        # no occupied slots in epoch 1
        assert epoch1_state.inferred_total_active_stake == 5

    def test_inferred_total_active_stake_close_to_true_total_stake(self):
        PRINT_DEBUG = False

        seed = 0
        N = 3
        EPOCHS = 2

        np.random.seed(seed)

        stake = np.array((np.random.pareto(10, N) + 1) * 1000, dtype=np.int64)
        coins = [Coin(sk=i, value=int(s)) for i, s in enumerate(stake)]

        config = Config.cryptarchia_v0_0_1(stake.sum() * 2).replace(k=40)
        genesis = mk_genesis_state(coins)

        nodes = [TestNode(config, genesis, c) for c in coins]

        T = config.epoch_length * EPOCHS
        slot_leaders = np.zeros(T, dtype=np.int32)
        for slot in map(Slot, range(T)):
            proposed_blocks = [n.on_slot(slot) for n in nodes]
            slot_leaders[slot.absolute_slot] = N - proposed_blocks.count(None)

            # now deliver the proposed blocks
            for n_idx, node in enumerate(nodes):
                # shuffle proposed blocks to simulate random delivery
                block_order = list(range(N))
                np.random.shuffle(block_order)
                for block_idx in block_order:
                    if block := proposed_blocks[block_idx]:
                        node.on_block(block)

        # Instead of inspecting state of each node, we group the nodes by their
        # tip, and select a representative for each group to inspect.
        #
        # This makes debugging with large number of nodes more maneagable.

        grouped_by_tip = _group_by(nodes, lambda n: n.follower.tip_id())
        for group in grouped_by_tip.values():
            ref_node = group[0]
            ref_epoch_state = ref_node.epoch_state(Slot(T))
            for node in group:
                assert node.follower.tip_state() == ref_node.follower.tip_state()
                assert node.epoch_state(Slot(T)) == ref_epoch_state

        reps = [g[0] for g in grouped_by_tip.values()]

        if PRINT_DEBUG:
            print()
            print("seed", seed)
            print(f"T={T}, EPOCHS={EPOCHS}")
            print(
                f"lottery stats",
                f"mean={slot_leaders.mean():.3f}",
                f"var={slot_leaders.var():.3f}",
            )
            print("true total stake\t", stake.sum())
            print("D_0\t", config.initial_total_stake)

            inferred_stake_by_epoch_by_rep = [
                [
                    r.epoch_state(Slot(e * config.epoch_length)).total_stake()
                    for e in range(EPOCHS + 1)
                ]
                for r in reps
            ]
            print(
                f"D_{list(range(EPOCHS + 1))}\n\t",
                "\n\t".join(
                    [
                        f"Rep {i}: {stakes}"
                        for i, stakes in inferred_stake_by_epoch_by_rep
                    ]
                ),
            )
            print("true leader count\t", slot_leaders.sum())
            print(
                "follower leader counts\t",
                [r.follower.tip_state().leader_count for r in reps],
            )

        assert all(
            slot_leaders.sum() + 1 == len(n.follower.ledger_state) for n in nodes
        ), f"{slot_leaders.sum() + 1}!={[len(n.follower.ledger_state) for n in nodes]}"

        for node in reps:
            inferred_stake = node.epoch_state(Slot(T)).total_active_stake()
            pct_err = (
                abs(stake.sum() - inferred_stake) / config.initial_total_active_stake
            )
            eps = (1 - config.total_active_stake_learning_rate) ** EPOCHS
            assert pct_err < eps, f"pct_err={pct_err} < eps={eps}"


def _group_by(iterable, key):
    import itertools

    return {
        k: list(group) for k, group in itertools.groupby(sorted(iterable, key=key), key)
    }
