from typing import List, Sequence

from eth2spec.deneb.mainnet import KZGProof as Proof, BLSFieldElement
from eth2spec.utils import bls

from da.kzg_rs.common import G1, BLS_MODULUS
from da.kzg_rs.fft import fft, ifft, fft_g1, ifft_g1
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
    vector_x_extended = global_parameters + [bls.multiply(bls.Z1(), 0) for _ in range(len(global_parameters))]
    vector_x_extended_fft = fft_g1(vector_x_extended, roots_of_unity, BLS_MODULUS)
    return vector_x_extended_fft


def toeplitz2(coefficients: List[G1], roots_of_unity: Sequence[int], extended_vector: Sequence[G1]) -> List[G1]:
    assert is_power_of_two(len(coefficients))
    toeplitz_coefficients_fft = fft(coefficients, roots_of_unity, BLS_MODULUS)
    return [bls.multiply(v, c) for v, c in zip(extended_vector, toeplitz_coefficients_fft)]


def toeplitz3(h_extended_fft: Sequence[G1], roots_of_unity: Sequence[int], polynomial_degree: int) -> List[G1]:
    return ifft_g1(h_extended_fft, roots_of_unity, BLS_MODULUS)[:polynomial_degree]


def fk20_generate_proofs(
        polynomial: Polynomial, global_parameters: List[G1], roots_of_unity: Sequence[int]
) -> List[Proof]:
    polynomial_degree = len(polynomial)
    assert len(roots_of_unity) >= 2 * polynomial_degree
    assert len(global_parameters) >= polynomial_degree
    assert is_power_of_two(len(polynomial))

    # 1 - Build toeplitz matrix for h values
    # 1.1 y = dft([s^d-1, s^d-2, ..., s, 1, *[0 for _ in len(polynomial)]])
    # 1.2 z = dft([*[0 for _ in len(polynomial)], f1, f2, ..., fd])
    # 1.3 u = y * v * roots_of_unity(len(polynomial)*2)
    global_parameters = [*global_parameters[polynomial_degree-2::-1], bls.multiply(bls.Z1(), 0)]
    extended_vector = toeplitz1(global_parameters, roots_of_unity[:polynomial_degree*2], polynomial_degree)
    # 2 - Build circulant matrix with the polynomial coefficients (reversed N..n, and padded)
    toeplitz_coefficients = [
        polynomial.coefficients[-1], *(0 for _ in range(polynomial_degree+1)), *polynomial.coefficients[1:-1]
    ]
    h_extended_vector = toeplitz2(toeplitz_coefficients, roots_of_unity[:len(extended_vector)], extended_vector)
    # 3 - Perform fft and nub the tail half as it is padding
    h_vector = toeplitz3(h_extended_vector, roots_of_unity[:len(h_extended_vector)], polynomial_degree)
    # 4 - proof are the dft of the h vector
    proofs = fft_g1(h_vector, roots_of_unity[:polynomial_degree], BLS_MODULUS)
    proofs = [Proof(bls.G1_to_bytes48(proof)) for proof in proofs]
    return proofs
