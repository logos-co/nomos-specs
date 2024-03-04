from typing import List

import eth2spec.eip7594.mainnet
from eth2spec.eip7594.mainnet import BLSFieldElement
from py_ecc.bls.typing import G1Uncompressed, G2Uncompressed
from remerkleable.basic import uint64

from da.kzg_rs.fft import compute_roots_of_unity, compute_inverse_roots_of_unity
from da.kzg_rs.trusted_setup import generate_setup

G1 = G1Uncompressed
G2 = G2Uncompressed


BYTES_PER_FIELD_ELEMENT = 32
BLS_MODULUS = eth2spec.eip7594.mainnet.BLS_MODULUS
GLOBAL_PARAMETERS: List[G1]
GLOBAL_PARAMETERS_G2: List[G2]
# secret is fixed but this should come from a different synchronization protocol
GLOBAL_PARAMETERS, GLOBAL_PARAMETERS_G2 = map(list, generate_setup(1024, 8, 1987))
ROOTS_OF_UNITY: List[int] = compute_roots_of_unity(2, BLS_MODULUS, 4096)
INVERSE_ROOTS_OF_UNITY: List[int] = compute_inverse_roots_of_unity(2, BLS_MODULUS, 4096)
