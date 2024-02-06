from unittest import TestCase

import numpy as np

from .cryptarchia import Leader, Config, EpochState, LedgerState, Coin, phi, TimeConfig


class TestLeader(TestCase):
    def test_slot_leader_statistics(self):
        epoch = EpochState(
            stake_distribution_snapshot=LedgerState(
                total_stake=1000,
            ),
            nonce_snapshot=LedgerState(nonce=b"1010101010"),
        )

        f = 0.05
        config = Config(
            k=10,
            active_slot_coeff=f,
            epoch_stake_distribution_stabilization=4,
            epoch_period_nonce_buffer=3,
            epoch_period_nonce_stabilization=3,
            time=TimeConfig(slot_duration=1, chain_start_time=0),
        )
        l = Leader(config=config, coin=Coin(sk=0, value=10))

        # We'll use the Margin of Error equation to decide how many samples we need.
        # https://en.wikipedia.org/wiki/Margin_of_error
        margin_of_error = 1e-4
        p = phi(f=f, alpha=10 / 1000)
        std = np.sqrt(p * (1 - p))
        Z = 3  # we want 3 std from the mean to be within the margin of error
        N = int((Z * std / margin_of_error) ** 2)

        # After N slots, the measured leader rate should be within the interval `p +- margin_of_error` with high probabiltiy
        leader_rate = (
            sum(l.try_prove_slot_leader(epoch, slot) is not None for slot in range(N))
            / N
        )
        assert (
            abs(leader_rate - p) < margin_of_error
        ), f"{leader_rate} != {p}, err={abs(leader_rate - p)} > {margin_of_error}"
