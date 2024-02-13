from itertools import batched
from typing import List, Sequence

import eth2spec.eip7594.mainnet
from eth2spec.eip7594.mainnet import (
    bit_reversal_permutation, KZG_SETUP_G1_LAGRANGE, Polynomial,
    BYTES_PER_FIELD_ELEMENT, bytes_to_bls_field, BLSFieldElement, compute_kzg_proof_impl,
    compute_roots_of_unity, verify_kzg_proof_impl
)
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof
from eth2spec.eip7594.minimal import evaluate_polynomial_in_evaluation_form
from eth2spec.utils import bls
from remerkleable.basic import uint64
from contextlib import contextmanager

from da.common import Chunk


@contextmanager
def setup_field_elements(new_value: int):
    """
    Override ethspecs setup to fit the variable sizes for our scheme
    """
    field_elements_old_value = eth2spec.eip7594.mainnet.FIELD_ELEMENTS_PER_BLOB
    minimal_field_elements_old_value = eth2spec.eip7594.minimal.FIELD_ELEMENTS_PER_BLOB
    eth2spec.eip7594.mainnet.FIELD_ELEMENTS_PER_BLOB = new_value
    eth2spec.eip7594.minimal.FIELD_ELEMENTS_PER_BLOB = new_value
    setup_old_value = eth2spec.eip7594.mainnet.KZG_SETUP_G1_LAGRANGE
    eth2spec.eip7594.mainnet.KZG_SETUP_G1_LAGRANGE = eth2spec.eip7594.mainnet.KZG_SETUP_G1_LAGRANGE[:new_value]
    yield
    eth2spec.eip7594.mainnet.FIELD_ELEMENTS_PER_BLOB = field_elements_old_value
    eth2spec.eip7594.minimal.FIELD_ELEMENTS_PER_BLOB = minimal_field_elements_old_value
    eth2spec.eip7594.mainnet.KZG_SETUP_G1_LAGRANGE = setup_old_value

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


def __compute_single_proof(
        polynomial: Polynomial,
        roots_of_unity: Sequence[BLSFieldElement],
        index: int
) -> Proof:
    with setup_field_elements(len(polynomial)):
        evaluation_challenge = roots_of_unity[index]
        proof, _ = compute_kzg_proof_impl(polynomial, evaluation_challenge)
        return proof


def compute_kzg_proofs(b: bytearray) -> List[Proof]:
    assert len(b) % BYTES_PER_FIELD_ELEMENT == 0
    polynomial = bytes_to_polynomial(b)
    roots_of_unity_brp = bit_reversal_permutation(compute_roots_of_unity(uint64(len(polynomial))))
    return [
        __compute_single_proof(polynomial, roots_of_unity_brp, i)
        for i in range(len(b)//BYTES_PER_FIELD_ELEMENT)
    ]


def __verify_single_proof(polynomial: Polynomial, proof: Proof, commitment: Commitment, index: int, roots_of_unity: Sequence[BLSFieldElement]) -> bool:
    challenge = roots_of_unity[index]
    with setup_field_elements(len(polynomial)):
        y = evaluate_polynomial_in_evaluation_form(polynomial, challenge)
        return verify_kzg_proof_impl(commitment, challenge, y, proof)


def verify_proofs(b: bytearray, commitment: Commitment, proofs: Sequence[Proof]) -> bool:
    polynomial = bytes_to_polynomial(b)
    roots_of_unity_brp = bit_reversal_permutation(compute_roots_of_unity(uint64(len(polynomial))))
    return all(
        __verify_single_proof(polynomial, proof, commitment, i, roots_of_unity_brp)
        for i, proof in enumerate(proofs)
    )

