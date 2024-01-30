from unittest import TestCase

import numpy as np

from .cryptarchia import Leader, LeaderConfig, EpochState, LedgerState, Coin, phi


class TestLeader(TestCase):
    def test_slot_leader_statistics(self):
        epoch_state = EpochState(
            stake_distribution_snapshot=LedgerState(
                total_stake=1000,
            ),
            nonce_snapshot=LedgerState(nonce=b"1010101010"),
        )

        f = 0.05
        leader_config = LeaderConfig(active_slot_coeff=f)
        l = Leader(config=leader_config, coin=Coin(pk=0, value=10))

        # We'll use the Margin of Error equation to decide how many samples we need.
        # https://en.wikipedia.org/wiki/Margin_of_error
        margin_of_error = 1e-4
        p = phi(f=f, alpha=10 / 1000)
        std = np.sqrt(p * (1 - p))
        Z = 3  # we want 3 std from the mean to be within the margin of error
        N = int((Z * std / margin_of_error) ** 2)

        # After N slots, the measured leader rate should be within the interval `p +- margin_of_error` with high probabiltiy
        leader_rate = sum(l.is_slot_leader(epoch_state, slot) for slot in range(N)) / N
        assert (
            abs(leader_rate - p) < margin_of_error
        ), f"{leader_rate} != {p}, err={abs(leader_rate - p)} > {margin_of_error}"