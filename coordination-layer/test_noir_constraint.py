from unittest import TestCase

from .noir_constraint import NoirConstraint


class TestNoirCoinstraint(TestCase):
    def test_bigger(self):
        # simple constraint that proves we know a number bigger than the provided
        # public input.
        bigger = NoirConstraint("bigger")

        # x is the secret input, y is the public input
        proof = bigger.prove({"x": "5", "y": "3"})

        # The proof that we know an `x` that is bigger than `y` should verify
        # Note, we must provide the public input that was used in the proof.
        assert bigger.verify({"y": "3"}, proof)

        # If we change the public input, the proof fails to verify.
        assert not bigger.verify({"y": "4"}, proof)
