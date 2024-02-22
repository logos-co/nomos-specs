from functools import reduce
from itertools import batched
from typing import Sequence

from eth2spec.deneb.mainnet import bytes_to_bls_field, BLSFieldElement, KZGCommitment as Commitment, KZGProof as Proof
from eth2spec.utils import bls
from sympy import intt

from .common import BYTES_PER_FIELD_ELEMENT, G1, BLS_MODULUS
from .poly import Polynomial


def bytes_to_polynomial(b: bytearray) -> Polynomial:
    """
    Convert bytes to list of BLS field scalars.
    """
    assert len(b) % BYTES_PER_FIELD_ELEMENT == 0
    eval_form = [int(bytes_to_bls_field(b)) for b in batched(b, int(BYTES_PER_FIELD_ELEMENT))]
    coefficients = intt(eval_form, prime=BLS_MODULUS)
    return Polynomial(coefficients, BLS_MODULUS)


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
        element: BLSFieldElement,
        polynomial: Polynomial,
        global_parameters: Sequence[G1]
) -> Proof:
    # compute a witness polynomial in that satisfies `witness(x) = (f(x)-v)/(x-u)`
    f_x_v = polynomial - Polynomial([polynomial.eval(int(element)) % BLS_MODULUS], BLS_MODULUS)
    x_u = Polynomial([-element, BLSFieldElement(1)], BLS_MODULUS)
    witness, _ = f_x_v / x_u
    return g1_linear_combination(witness, global_parameters)
