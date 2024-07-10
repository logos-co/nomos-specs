from typing import List, Sequence

from eth2spec.deneb.mainnet import KZGProof as Proof, BLSFieldElement
from eth2spec.utils import bls

from da.kzg_rs.common import G1, BLS_MODULUS, PRIMITIVE_ROOT
from da.kzg_rs.fft import fft, fft_g1, ifft_g1
from da.kzg_rs.poly import Polynomial
from da.kzg_rs.roots import compute_roots_of_unity
from da.kzg_rs.utils import is_power_of_two


def __toeplitz1(global_parameters: List[G1], polynomial_degree: int) -> List[G1]:
    """
    This part can be precomputed for different global_parameters lengths depending on polynomial degree of powers of two.
    :param global_parameters:
    :param roots_of_unity:
    :param polynomial_degree:
    :return:
    """
    assert len(global_parameters) == polynomial_degree
    # algorithm only works on powers of 2 for dft computations
    assert is_power_of_two(len(global_parameters))
    roots_of_unity = compute_roots_of_unity(PRIMITIVE_ROOT, polynomial_degree*2, BLS_MODULUS)
    vector_x_extended = global_parameters + [bls.Z1() for _ in range(polynomial_degree)]
    vector_x_extended_fft = fft_g1(vector_x_extended, roots_of_unity, BLS_MODULUS)
    return vector_x_extended_fft


def __toeplitz2(coefficients: List[BLSFieldElement], extended_vector: Sequence[G1]) -> List[G1]:
    assert is_power_of_two(len(coefficients))
    roots_of_unity = compute_roots_of_unity(PRIMITIVE_ROOT, len(coefficients), BLS_MODULUS)
    toeplitz_coefficients_fft = fft(coefficients, roots_of_unity, BLS_MODULUS)
    return [bls.multiply(v, c) for v, c in zip(extended_vector, toeplitz_coefficients_fft)]


def __toeplitz3(h_extended_fft: Sequence[G1], polynomial_degree: int) -> List[G1]:
    roots_of_unity = compute_roots_of_unity(PRIMITIVE_ROOT, len(h_extended_fft), BLS_MODULUS)
    return ifft_g1(h_extended_fft, roots_of_unity, BLS_MODULUS)[:polynomial_degree]


def fk20_generate_proofs(
        polynomial: Polynomial, global_parameters: List[G1]
) -> List[Proof]:
    """
    Generate all proofs for the polynomial points in batch.
    This method uses the fk20 algorthm from https://eprint.iacr.org/2023/033.pdf
    Disclaimer: It only works for polynomial degree of powers of two.
    :param polynomial: polynomial to generate proof for
    :param global_parameters: setup generated parameters
    :return: list of proof for each point in the polynomial
    """
    polynomial_degree = len(polynomial)
    assert len(global_parameters) >= polynomial_degree
    assert is_power_of_two(len(polynomial))

    # 1 - Build toeplitz matrix for h values
    # 1.1 y = dft([s^d-1, s^d-2, ..., s, 1, *[0 for _ in len(polynomial)]])
    # 1.2 z = dft([*[0 for _ in len(polynomial)], f1, f2, ..., fd])
    # 1.3 u = y * v * roots_of_unity(len(polynomial)*2)
    roots_of_unity = compute_roots_of_unity(PRIMITIVE_ROOT, polynomial_degree, BLS_MODULUS)
    global_parameters = list(reversed(global_parameters[:polynomial_degree]))
    extended_vector = __toeplitz1(global_parameters, polynomial_degree)
    # 2 - Build circulant matrix with the polynomial coefficients (reversed N..n, and padded)
    toeplitz_coefficients = [
        *(BLSFieldElement(0) for _ in range(polynomial_degree)),
        *polynomial.coefficients
    ]
    h_extended_vector = __toeplitz2(toeplitz_coefficients, extended_vector)
    # 3 - Perform fft and nub the tail half as it is padding
    h_vector = __toeplitz3(h_extended_vector, polynomial_degree)
    # 4 - proof are the dft of the h vector
    proofs = fft_g1(h_vector, roots_of_unity, BLS_MODULUS)
    proofs = [Proof(bls.G1_to_bytes48(proof)) for proof in proofs]
    return proofs
