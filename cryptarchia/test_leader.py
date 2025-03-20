from unittest import TestCase

import numpy as np

from .cryptarchia import Leader, EpochState, LedgerState, Note, phi, Slot
from .test_common import mk_config


class TestLeader(TestCase):
    def test_slot_leader_statistics(self):
        epoch = EpochState(
            stake_distribution_snapshot=LedgerState(block=None),
            nonce_snapshot=LedgerState(block=None, nonce=b"1010101010"),
            inferred_total_active_stake=1000,
        )

        note = Note(sk=0, value=10)
        f = 0.05
        l = Leader(
            config=mk_config([note]).replace(active_slot_coeff=f),
            note=note,
        )

        # We'll use the Margin of Error equation to decide how many samples we need.
        # https://en.wikipedia.org/wiki/Margin_of_error
        margin_of_error = 1e-4
        p = phi(f=f, alpha=10 / epoch.total_active_stake())
        std = np.sqrt(p * (1 - p))
        Z = 3  # we want 3 std from the mean to be within the margin of error
        N = int((Z * std / margin_of_error) ** 2)

        # After N slots, the measured leader rate should be within the
        # interval `p +- margin_of_error` with high probabiltiy
        leader_rate = (
            sum(
                l.try_prove_slot_leader(epoch, Slot(slot), bytes(32)) is not None
                for slot in range(N)
            )
            / N
        )
        assert (
            abs(leader_rate - p) < margin_of_error
        ), f"{leader_rate} != {p}, err={abs(leader_rate - p)} > {margin_of_error}"
