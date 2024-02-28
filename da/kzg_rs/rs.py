from typing import Sequence

from eth2spec.deneb.mainnet import BLSFieldElement

from .common import G1
from .poly import Polynomial
from .fft import fft, ifft


def encode(polynomial: Polynomial, factor: int, roots_of_unity: Sequence[BLSFieldElement]) -> Polynomial:
    assert factor >= 2
    assert len(polynomial)*factor <= len(roots_of_unity)
    extended_polynomial_coefficients = polynomial.coefficients + [0]*(len(polynomial)*factor-1)
    extended_polynomial_coefficients = fft(extended_polynomial_coefficients, polynomial.modulus, roots_of_unity)
    return Polynomial(extended_polynomial_coefficients, modulus=polynomial.modulus)


def decode(polynomial: Polynomial, factor: int, roots_of_unity: Sequence[BLSFieldElement]) -> Polynomial:
    coefficients = ifft(polynomial.coefficients, polynomial.modulus, factor, roots_of_unity)
    return Polynomial(coefficients=coefficients, modulus=polynomial.modulus)

