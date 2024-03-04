from typing import Sequence, List

import scipy.interpolate
from eth2spec.deneb.mainnet import BLSFieldElement

from .common import G1, BLS_MODULUS
from .poly import Polynomial
from .fft import fft, ifft

ExtendedData = Sequence[BLSFieldElement]


def encode(polynomial: Polynomial, factor: int, roots_of_unity: Sequence[BLSFieldElement]) -> ExtendedData:
    assert factor >= 2
    assert len(polynomial)*factor <= len(roots_of_unity)
    extended_polynomial_evaluations = polynomial.coefficients + [0]*(len(polynomial)*factor-1)
    extended_polynomial_evaluations = [
        BLSFieldElement(e % polynomial.modulus)
        for e in fft(extended_polynomial_evaluations, polynomial.modulus, roots_of_unity)
    ]
    return extended_polynomial_evaluations


def __interpolate(evaluations: List[int], roots_of_unity: List[int], modulus=BLS_MODULUS) -> List[int]:
    """
    Lagrange interpolation
    """
    assert len(evaluations) <= len(roots_of_unity)
    coefs = scipy.interpolate.lagrange(roots_of_unity[:len(evaluations)], evaluations).coef
    return [coef % modulus for coef in coefs]


def decode(encoded: ExtendedData, roots_of_unity: Sequence[BLSFieldElement], original_len: int) -> Polynomial:
    coefs = __interpolate(list(map(int, encoded)), list(map(int, roots_of_unity)))
    return Polynomial([int(c) for c in coefs], BLS_MODULUS)

