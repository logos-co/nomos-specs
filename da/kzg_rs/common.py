from typing import List

import eth2spec.eip7594.mainnet
from eth2spec.eip7594.mainnet import BLSFieldElement, compute_roots_of_unity
from py_ecc.bls.typing import G1Uncompressed, G2Uncompressed
from remerkleable.basic import uint64
from da.kzg_rs.trusted_setup import generate_setup

G1 = G1Uncompressed
G2 = G2Uncompressed


BYTES_PER_FIELD_ELEMENT = 32
GLOBAL_PARAMETERS: List[G1]
GLOBAL_PARAMETERS_G2: List[G2]
# secret is fixed but this should come from a different synchronization protocol
GLOBAL_PARAMETERS, GLOBAL_PARAMETERS_G2 = map(list, generate_setup(1024, 8, 1987))
ROOTS_OF_UNITY: List[BLSFieldElement] = list(compute_roots_of_unity(uint64(4096)))
BLS_MODULUS = eth2spec.eip7594.mainnet.BLS_MODULUS
