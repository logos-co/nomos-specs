from itertools import batched
from typing import List, Sequence

import eth2spec.eip7594.minimal
from eth2spec.eip7594.mainnet import (
    bit_reversal_permutation,
    KZG_SETUP_G1_LAGRANGE,
    KZG_ENDIANNESS,
    Polynomial,
    BYTES_PER_FIELD_ELEMENT,
    bytes_to_bls_field,
    BLSFieldElement,
    compute_roots_of_unity,
    verify_kzg_proof_impl,
    KZGCommitment as Commitment,
    KZGProof as Proof,
    BLS_MODULUS, div, bls_modular_inverse, KZG_SETUP_G2_MONOMIAL
)
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
    return Polynomial(bytes_to_bls_field(b) for b in batched(b, int(BYTES_PER_FIELD_ELEMENT)))


def __evaluate_polynomial_in_evaluation_form(
        polynomial: Polynomial,
        z: BLSFieldElement,
        roots_of_unity: Sequence[BLSFieldElement]) -> BLSFieldElement:
    """
    Evaluate a polynomial (in evaluation form) at an arbitrary point ``z``.
    - When ``z`` is in the domain, the evaluation can be found by indexing the polynomial at the
    position that ``z`` is in the domain.
    - When ``z`` is not in the domain, the barycentric formula is used:
       f(z) = (z**WIDTH - 1) / WIDTH  *  sum_(i=0)^WIDTH  (f(DOMAIN[i]) * DOMAIN[i]) / (z - DOMAIN[i])
    """
    width = len(polynomial)
    inverse_width = bls_modular_inverse(BLSFieldElement(width))

    # If we are asked to evaluate within the domain, we already know the answer
    if z in roots_of_unity:
        eval_index = roots_of_unity.index(z)
        return BLSFieldElement(polynomial[eval_index])

    result = 0
    for i in range(width):
        a = BLSFieldElement(int(polynomial[i]) * int(roots_of_unity[i]) % BLS_MODULUS)
        b = BLSFieldElement((int(BLS_MODULUS) + int(z) - int(roots_of_unity[i])) % BLS_MODULUS)
        result += int(div(a, b) % BLS_MODULUS)
    result = result * int(BLS_MODULUS + pow(z, width, BLS_MODULUS) - 1) * int(inverse_width)
    return BLSFieldElement(result % BLS_MODULUS)


def __compute_quotient_eval_within_domain(z: BLSFieldElement,
                                        polynomial: Polynomial,
                                        y: BLSFieldElement,
                                        roots_of_unity: Sequence[BLSFieldElement]
                                        ) -> BLSFieldElement:
    """
    Given `y == p(z)` for a polynomial `p(x)`, compute `q(z)`: the KZG quotient polynomial evaluated at `z` for the
    special case where `z` is in roots of unity.

    For more details, read https://dankradfeist.de/ethereum/2021/06/18/pcs-multiproofs.html section "Dividing
    when one of the points is zero". The code below computes q(x_m) for the roots of unity special case.
    """
    result = 0
    for i, omega_i in enumerate(roots_of_unity):
        if omega_i == z:  # skip the evaluation point in the sum
            continue

        f_i = int(BLS_MODULUS) + int(polynomial[i]) - int(y) % BLS_MODULUS
        numerator = f_i * int(omega_i) % BLS_MODULUS
        denominator = int(z) * (int(BLS_MODULUS) + int(z) - int(omega_i)) % BLS_MODULUS
        result += int(div(BLSFieldElement(numerator), BLSFieldElement(denominator)))

    return BLSFieldElement(result % BLS_MODULUS)


def bytes_to_kzg_commitment(b: bytearray) -> Commitment:
    return g1_lincomb(
        bit_reversal_permutation(KZG_SETUP_G1_LAGRANGE), bytes_to_polynomial(b)
    )


def _compute_single_proof(
        polynomial: Polynomial,
        roots_of_unity: Sequence[BLSFieldElement],
        index: int
) -> Proof:
    """
    Helper function for `compute_kzg_proof()` and `compute_blob_kzg_proof()`.
    """

    # For all x_i, compute p(x_i) - p(z)
    u = roots_of_unity[index]
    y = BLSFieldElement(polynomial[index])
    # y = __evaluate_polynomial_in_evaluation_form(polynomial, u, roots_of_unity)
    polynomial_shifted = [BLSFieldElement((int(p) - int(y)) % BLS_MODULUS) for p in polynomial]

    # For all x_i, compute (x_i - z)
    denominator_poly = [BLSFieldElement((int(x) - int(u)) % BLS_MODULUS) for x in roots_of_unity]

    # Compute the quotient polynomial directly in evaluation form
    quotient_polynomial = [BLSFieldElement(0)] * len(polynomial)
    for i, (a, b) in enumerate(zip(polynomial_shifted, denominator_poly)):
        if b == 0:
            # The denominator is zero hence `z` is a root of unity: we must handle it as a special case
            quotient_polynomial[i] = __compute_quotient_eval_within_domain(roots_of_unity[i], polynomial, y, roots_of_unity)
        else:
            # Compute: q(x_i) = (p(x_i) - p(z)) / (x_i - z).
            quotient_polynomial[i] = div(a, b)

    return Proof(g1_lincomb(bit_reversal_permutation(KZG_SETUP_G1_LAGRANGE), quotient_polynomial))


def compute_kzg_proofs(b: bytearray) -> List[Proof]:
    assert len(b) % BYTES_PER_FIELD_ELEMENT == 0
    polynomial = bytes_to_polynomial(b)
    roots_of_unity_brp = bit_reversal_permutation(compute_roots_of_unity(uint64(len(polynomial))))
    return [
        _compute_single_proof(polynomial, roots_of_unity_brp, i)
        for i in range(len(b)//BYTES_PER_FIELD_ELEMENT)
    ]

def __verify_kzg_proof_impl(commitment: Commitment,
                          z: BLSFieldElement,
                          y: BLSFieldElement,
                          proof: Proof) -> bool:
    """
    Verify KZG proof that ``p(z) == y`` where ``p(z)`` is the polynomial represented by ``polynomial_kzg``.
    """
    # Verify: P - y = Q * (X - z)
    X_minus_z = bls.add(
        bls.bytes96_to_G2(KZG_SETUP_G2_MONOMIAL[1]),
        bls.multiply(bls.G2(), (BLS_MODULUS - z) % BLS_MODULUS),
    )
    P_minus_y = bls.add(bls.bytes48_to_G1(commitment), bls.multiply(bls.G1(), (BLS_MODULUS - y) % BLS_MODULUS))
    return bls.pairing_check([
        [P_minus_y, bls.neg(bls.G2())],
        [bls.bytes48_to_G1(proof), X_minus_z]
    ])


def verify_single_proof(polynomial: Polynomial, proof: Proof, commitment: Commitment, index: int, roots_of_unity: Sequence[BLSFieldElement]) -> bool:
    u = roots_of_unity[index]
    y = __evaluate_polynomial_in_evaluation_form(polynomial, u, roots_of_unity)
    return __verify_kzg_proof_impl(commitment, u, y, proof)


def verify_proofs(b: bytearray, commitment: Commitment, proofs: Sequence[Proof]) -> bool:
    polynomial = bytes_to_polynomial(b)
    roots_of_unity_brp = bit_reversal_permutation(compute_roots_of_unity(uint64(len(polynomial))))
    return all(
        verify_single_proof(polynomial, proof, commitment, i, roots_of_unity_brp)
        for i, proof in enumerate(proofs)
    )
