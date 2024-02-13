from itertools import batched
from typing import List, Sequence

from eth2spec.eip7594.mainnet import (
    bit_reversal_permutation, KZG_SETUP_G1_LAGRANGE, Polynomial,
    BYTES_PER_FIELD_ELEMENT, bytes_to_bls_field, BLSFieldElement, compute_kzg_proof_impl, KZG_ENDIANNESS,
)
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof
from eth2spec.utils import bls


class Polynomial(List[BLSFieldElement]):
    pass


def g1_lincomb(points: Sequence[Commitment], scalars: Sequence[BLSFieldElement]) -> Commitment:
    """
    BLS multiscalar multiplication. This function can be optimized using Pippenger's algorithm and variants.
    """
    # we assert to have more points available than elements,
    # this is dependent on the available kzg setup size
    assert len(points) >= len(scalars)
    result = bls.Z1()
    for x, a in zip(points, scalars):
        result = bls.add(result, bls.multiply(bls.bytes48_to_G1(x), a))
    return Commitment(bls.G1_to_bytes48(result))


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


def compute_kzg_proofs(b: bytearray, commitment: Commitment) -> List[Proof]:
    assert len(b) % BYTES_PER_FIELD_ELEMENT == 0
    polynomial = bytes_to_polynomial(b)
    return [
        compute_kzg_proof_impl(
            polynomial,
            bytes_to_bls_field(i.to_bytes(length=BYTES_PER_FIELD_ELEMENT, byteorder=KZG_ENDIANNESS))
        )[0]
        for i in range(len(b)//BYTES_PER_FIELD_ELEMENT)
    ]

