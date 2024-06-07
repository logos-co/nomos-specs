from typing import List, Sequence

from eth2spec.deneb.mainnet import KZGProof as Proof

from da.kzg_rs.common import G1, BLS_MODULUS
from da.kzg_rs.fft import fft
from da.kzg_rs.poly import Polynomial
from da.kzg_rs.utils import is_power_of_two


def toeplitz1(global_parameters: List[G1], roots_of_unity: Sequence[int], polynomial_degree: int) -> List[G1]:
    """
    This part can be precomputed for different global_parameters lengths depending on polynomial degree of powers of two.
    :param global_parameters:
    :param roots_of_unity:
    :param polynomial_degree:
    :return:
    """
    assert len(roots_of_unity) >= 2 * polynomial_degree
    assert len(global_parameters) >= polynomial_degree
    global_parameters = global_parameters[:polynomial_degree]
    # algorithm only works on powers of 2 for dft computations
    assert is_power_of_two(len(global_parameters))
    roots_of_unity = roots_of_unity[:2*polynomial_degree]
    vector_x_extended = global_parameters + [G1(0) for _ in range(len(global_parameters))]
    vector_x_extended_fft = fft(vector_x_extended, BLS_MODULUS, roots_of_unity)
    return vector_x_extended_fft

def fk20_generate_proofs(polynomial: Polynomial) -> List[Proof]:
    # 1 - Build toeplitz matrix for h values
    # 1.1 y = dft([s^d-1, s^d-2, ..., s, 1, *[0 for _ in len(polynomial)]])
    # 1.2 z = dft([*[0 for _ in len(polynomial)], f1, f2, ..., fd])
    # 1.3 u = y * v * roots_of_unity(len(polynomial)*2)
    # 2 - Build circulant matrix with the polynomial coefficients (reversed N..n, and padded)
    # 3 - Perform fft and nub the tail half as it is padding
    pass