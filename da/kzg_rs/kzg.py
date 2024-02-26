from functools import reduce
from itertools import batched
from typing import Sequence

from eth2spec.deneb.mainnet import bytes_to_bls_field, BLSFieldElement, KZGCommitment as Commitment, KZGProof as Proof, \
    verify_kzg_proof, KZG_SETUP_G2_MONOMIAL
from eth2spec.utils import bls
from sympy import intt

from .common import BYTES_PER_FIELD_ELEMENT, G1, BLS_MODULUS, GLOBAL_PARAMETERS_G2
from .poly import Polynomial


def bytes_to_polynomial(bytes: bytearray) -> Polynomial:
    """
    Convert bytes to list of BLS field scalars.
    """
    assert len(bytes) % BYTES_PER_FIELD_ELEMENT == 0
    eval_form = [int(bytes_to_bls_field(b)) for b in batched(bytes, int(BYTES_PER_FIELD_ELEMENT))]
    return Polynomial.from_evaluations(eval_form, BLS_MODULUS)


def g1_linear_combination(polynomial: Polynomial[BLSFieldElement], global_parameters: Sequence[G1]) -> Commitment:
    """
    BLS multiscalar multiplication.
    """
    # we assert to have more points available than elements,
    # this is dependent on the available kzg setup size
    assert len(polynomial) <= len(global_parameters)
    point = reduce(
        bls.add,
        (bls.multiply(g, p) for g, p in zip(global_parameters, polynomial)),
        bls.Z1()
    )
    return Commitment(bls.G1_to_bytes48(point))


def bytes_to_commitment(b: bytearray, global_parameters: Sequence[G1]) -> Commitment:
    poly = bytes_to_polynomial(b)
    return g1_linear_combination(poly, global_parameters)


def generate_element_proof(
        element_index: int,
        polynomial: Polynomial,
        global_parameters: Sequence[G1],
        roots_of_unity: Sequence[BLSFieldElement],
) -> Proof:
    # compute a witness polynomial in that satisfies `witness(x) = (f(x)-v)/(x-u)`
    u = int(roots_of_unity[element_index])
    v = polynomial.eval(u)
    f_x_v = polynomial - Polynomial([v], BLS_MODULUS)
    x_u = Polynomial([-u, 1], BLS_MODULUS)
    witness, _ = f_x_v / x_u
    return g1_linear_combination(witness, global_parameters)


def verify_element_proof(
        polynomial: Polynomial,
        commitment: Commitment,
        proof: Proof,
        element_index: int,
        roots_of_unity: Sequence[BLSFieldElement],
) -> bool:
    u = int(roots_of_unity[element_index])
    v = polynomial.eval(u)
    commitment_check_G1 = bls.bytes48_to_G1(commitment) - bls.multiply(bls.G1(), v)
    proof_check_g2 = bls.add(
        GLOBAL_PARAMETERS_G2[1],
        bls.neg(bls.multiply(bls.G2(), u))
    )
    return bls.pairing_check([
        # G2 here needs to be negated due to library requirements as pairing_check([[G1, -G2], [G1, G2]])
        [commitment_check_G1, bls.neg(bls.G2())],
        [bls.bytes48_to_G1(proof), proof_check_g2],
    ])
