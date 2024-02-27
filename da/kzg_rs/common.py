from typing import List

import eth2spec.eip7594.mainnet
from eth2spec.eip7594.mainnet import BLSFieldElement, compute_roots_of_unity
from eth2spec.utils import bls
from py_ecc.bls.typing import G1Uncompressed, G2Uncompressed
from remerkleable.basic import uint64
import random

G1 = G1Uncompressed
G2 = G2Uncompressed
def generate_one_sided_setup(length, secret, generator=bls.G1()):
    o = [generator]
    for i in range(1, length):
        o.append(bls.multiply(o[-1], secret))
    return o

# Generate a trusted setup with the given secret
def generate_setup(G1_length, G2_length, secret):
    return (
        generate_one_sided_setup(G1_length, secret, bls.G1()),
        generate_one_sided_setup(G2_length, secret, bls.G2()),
    )

def linear_combination(points, coeffs, zero=bls.Z1()):
    o = zero
    for point, coeff in zip(points, coeffs):
        o = bls.add(o, bls.multiply(point, coeff))
    return o

# Verifies the integrity of a setup
def verify_setup(setup):
    G1_setup, G2_setup = setup
    G1_random_coeffs = [random.randrange(2**40) for _ in range(len(G1_setup) - 1)]
    G1_lower = linear_combination(G1_setup[:-1], G1_random_coeffs, bls.Z1())
    G1_upper = linear_combination(G1_setup[1:], G1_random_coeffs, bls.Z1())
    G2_random_coeffs = [random.randrange(2**40) for _ in range(len(G2_setup) - 1)]
    G2_lower = linear_combination(G2_setup[:-1], G2_random_coeffs, bls.Z2())
    G2_upper = linear_combination(G2_setup[1:], G2_random_coeffs, bls.Z2())
    return (
        G1_setup[0] == bls.G1() and 
        G2_setup[0] == bls.G2() and 
        b.pairing(G2_lower, G1_upper) == b.pairing(G2_upper, G1_lower)
    )

BYTES_PER_FIELD_ELEMENT = 32
# we reversed the trusted setup here as np uses a biggest element first approach
GLOBAL_PARAMETERS: List[G1]
GLOBAL_PARAMETERS_G2: List[G2]
GLOBAL_PARAMETERS, GLOBAL_PARAMETERS_G2 = generate_setup(1024, 8, 1987)
ROOTS_OF_UNITY: List[BLSFieldElement] = list(compute_roots_of_unity(uint64(4096)))
BLS_MODULUS = eth2spec.eip7594.mainnet.BLS_MODULUS
