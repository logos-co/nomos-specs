from eth2spec.utils import bls

from .common import BLS_MODULUS
from .poly import Polynomial
from functools import reduce


def generator_polynomial(n, k, gen=bls.G1()) -> Polynomial:
    """
    Generate the generator polynomial for RS codes
    g(x) = (x-α^1)(x-α^2)...(x-α^(n-k))
    """
    g = Polynomial([bls.Z1()], modulus=BLS_MODULUS)
    return reduce(
        Polynomial.__mul__,
        (Polynomial([bls.Z1(), bls.multiply(gen, alpha)], modulus=BLS_MODULUS) for alpha in range(1, n-k+1)),
        initial=g
    )


def encode(m: Polynomial, g: Polynomial, n: int, k: int) -> Polynomial:
    # mprime = q*g + b for some q
    xshift = Polynomial([bls.Z1(),  *[0 for _ in range(n-k)]], modulus=m.modulus)
    mprime = m * xshift
    _, b = m / g
    # subtract out b, so now c = q*g
    c = mprime - b
    # Since c is a multiple of g, it has (at least) n-k roots: α^1 through
    # α^(n-k)
    return c
