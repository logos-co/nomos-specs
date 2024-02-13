from itertools import batched
from typing import List

from eth2spec.eip7594.mainnet import (
    blob_to_kzg_commitment, g1_lincomb, bit_reversal_permutation, KZG_SETUP_G1_LAGRANGE, Polynomial,
    BYTES_PER_FIELD_ELEMENT, bytes_to_bls_field, BLSFieldElement,
)
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof


class Polynomial(List[BLSFieldElement]):
    pass


def bytes_to_polynomial(b: bytearray) -> Polynomial:
    """
    Convert bytes to list of BLS field scalars.
    """
    assert len(b) % BYTES_PER_FIELD_ELEMENT == 0
    return Polynomial(bytes_to_bls_field(b) for b in batched(b, BYTES_PER_FIELD_ELEMENT))


def bytes_to_kzg_commitment(b: bytearray) -> Commitment:
    return g1_lincomb(
        bit_reversal_permutation(KZG_SETUP_G1_LAGRANGE), bytes_to_polynomial(b)
    )
