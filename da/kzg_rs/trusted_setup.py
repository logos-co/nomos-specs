import random
from typing import Tuple, Sequence, Generator
from eth2spec.utils import bls
from itertools import accumulate, repeat


def __linear_combination(points, coeffs, zero=bls.Z1()):
    o = zero
    for point, coeff in zip(points, coeffs):
        o = bls.add(o, bls.multiply(point, coeff))
    return o


# Verifies the integrity of a setup
def verify_setup(setup) -> bool:
    g1_setup, g2_setup = setup
    g1_random_coefficients = [random.randrange(2**40) for _ in range(len(g1_setup) - 1)]
    g1_lower = __linear_combination(g1_setup[:-1], g1_random_coefficients, bls.Z1())
    g1_upper = __linear_combination(g1_setup[1:], g1_random_coefficients, bls.Z1())
    g2_random_coefficients = [random.randrange(2**40) for _ in range(len(g2_setup) - 1)]
    g2_lower = __linear_combination(g2_setup[:-1], g2_random_coefficients, bls.Z2())
    g2_upper = __linear_combination(g2_setup[1:], g2_random_coefficients, bls.Z2())
    return (
        g1_setup[0] == bls.G1() and
        g2_setup[0] == bls.G2() and
        bls.pairing_check([[g1_upper, bls.neg(g2_lower)], [g1_lower, g2_upper]])
    )


def generate_one_sided_setup(length, secret, generator=bls.G1()):
    def __take(gen):
        return (next(gen) for _ in range(length))

    secrets = repeat(secret)

    return __take(accumulate(secrets, bls.multiply, initial=generator))


# Generate a trusted setup with the given secret
def generate_setup(
        g1_length,
        g2_length,
        secret
) -> Tuple[Generator[bls.G1, None, None], Generator[bls.G2, None, None]]:
    return (
        generate_one_sided_setup(g1_length, secret, bls.G1()),
        generate_one_sided_setup(g2_length, secret, bls.G2()),
    )
