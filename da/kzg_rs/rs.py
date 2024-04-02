from typing import Sequence, Optional

from eth2spec.deneb.mainnet import BLSFieldElement
from .common import BLS_MODULUS
from .poly import Polynomial

ExtendedData = Sequence[Optional[BLSFieldElement]]


def encode(polynomial: Polynomial, factor: int, roots_of_unity: Sequence[int]) -> ExtendedData:
    """
    Encode a polynomial extending to the given factor
    Parameters:
        polynomial: Polynomial to be encoded
        factor: Encoding factor
        roots_of_unity: Powers of 2 sequence

    Returns:
        list: Extended data set
    """
    assert factor >= 2
    assert len(polynomial)*factor <= len(roots_of_unity)
    return [polynomial.eval(e) for e in roots_of_unity[:len(polynomial)*factor]]


def decode(encoded: ExtendedData, roots_of_unity: Sequence[BLSFieldElement], original_len: int) -> Polynomial:
    """
    Decode a polynomial from an extended data-set and the roots of unity, cap to original length

    Parameters:
        encoded: Extended data set
        roots_of_unity: Powers of 2 sequence
        original_len: Original length of the encoded polynomial

    Returns:
        Polynomial: original polynomial
    """
    encoded, roots_of_unity = zip(*((point, root) for point, root in zip(encoded, roots_of_unity) if point is not None))
    coefs = Polynomial.interpolate(list(map(int, encoded)), list(map(int, roots_of_unity)))[:original_len]
    return Polynomial([int(c) for c in coefs], BLS_MODULUS)
