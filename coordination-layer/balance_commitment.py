"""
This module holds the logic for building and verifying homomorphic balance commitments.
"""

from constraints import Constraint
from crypto import Field, Point, prf, hash_to_curve, pederson_commit, _str_to_vec


def balance_commitment(value: Field, blinding: Field, unit: Point):
    return pederson_commit(value, blinding, unit)


def fungibility_domain(unit: str, birth_cm: Field) -> Point:
    """The fungibility domain of this note"""
    return hash_to_curve("CL_NOTE_NULL", birth_cm, *_str_to_vec(unit))


def blinding(tx_rand: Field, nf_pk: Field) -> Field:
    """Blinding factor used in balance commitments"""
    return prf("CL_NOTE_BAL_BLIND", tx_rand, nf_pk)
