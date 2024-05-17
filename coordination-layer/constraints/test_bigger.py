from unittest import TestCase

from .bigger import Bigger


class TestBigger(TestCase):
    def test_bigger(self):
        bigger = Bigger(3)
        proof = bigger.prove(5)
        bigger.verify(proof)

        # If we try to reuse the proof for a different Bigger instance, it fails
        bigger_4 = Bigger(4)
        assert not bigger_4.verify(proof)
