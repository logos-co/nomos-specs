from typing import Sequence, List

import scipy.interpolate
from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import interpolate_polynomialcoeff
from .common import G1, BLS_MODULUS
from .poly import Polynomial

ExtendedData = Sequence[BLSFieldElement]


def encode(polynomial: Polynomial, factor: int, roots_of_unity: Sequence[BLSFieldElement]) -> ExtendedData:
    assert factor >= 2
    assert len(polynomial)*factor <= len(roots_of_unity)
    return [polynomial.eval(e) for e in roots_of_unity[:len(polynomial)*factor]]


def __interpolate(evaluations: List[int], roots_of_unity: List[int]) -> List[int]:
    """
    Lagrange interpolation
    """
    return list(map(int, interpolate_polynomialcoeff(roots_of_unity[:len(evaluations)], evaluations)))


def decode(encoded: ExtendedData, roots_of_unity: Sequence[BLSFieldElement], original_len: int) -> Polynomial:
    coefs = __interpolate(list(map(int, encoded)), list(map(int, roots_of_unity)))[:original_len]
    return Polynomial([int(c) for c in coefs], BLS_MODULUS)
