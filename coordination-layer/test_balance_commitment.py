from unittest import TestCase

from hypothesis import example, given, settings, strategies as st

from crypto import Field, hash_to_curve
from balance_commitment import balance_commitment


@st.composite
def field(draw):
    x = draw(st.integers(min_value=0, max_value=Field.ORDER - 1))
    return Field(x)


@st.composite
def point(draw):
    x = draw(field())
    return hash_to_curve("T", x)


class TestBalanceCommitment(TestCase):
    @given(r=field(), a=field(), b=field(), unit=point())
    @settings(max_examples=3)
    def test_value_additive(self, r, a, b, unit):
        print(r, a, b, unit)
        b1 = balance_commitment(r, a, unit)
        b2 = balance_commitment(r, b, unit)
        b3 = balance_commitment(r, a + b, unit)

        assert b1 + b2 == b3
