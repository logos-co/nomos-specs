"""
This module tests that all the hacks we introduced in our crypto mocks give us
the basic behaviour that we need.
"""

from unittest import TestCase


from crypto import Field, Point, hash_to_curve, prf


class TestCrypto(TestCase):
    def test_hash_to_curve(self):
        p1 = hash_to_curve("TEST", Field(0), Field(1), Field(2))
        p2 = hash_to_curve("TEST", Field(0), Field(1), Field(2))

        assert isinstance(p1, Point)

        assert p1 == p2

        p3 = hash_to_curve("TEST", Field(0), Field(1), Field(3))

        assert p1 != p3

    def test_prf(self):
        r1 = prf("TEST", Field(0), Field(1), Field(2))
        r2 = prf("TEST", Field(0), Field(1), Field(2))

        assert isinstance(r1, Field)
        assert r1 == r2

        r3 = prf("TEST", Field(0), Field(1), Field(3))
        assert r1 != r3
