"""
This module tests that all the hacks we introduced in our crypto mocks give us
the basic behaviour that we need.
"""

from unittest import TestCase


from crypto import hash_to_curve, Field


class TestCrypto(TestCase):
    def test_hash_to_curve(self):
        p1 = hash_to_curve(Field(0), Field(1), Field(2))
        p2 = hash_to_curve(Field(0), Field(1), Field(2))

        assert p1 == p2

        p3 = hash_to_curve(Field(0), Field(1), Field(3))

        assert p1 != p3
