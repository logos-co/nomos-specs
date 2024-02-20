from typing import List

import eth2spec.eip7594.mainnet
from eth2spec.eip7594.mainnet import KZG_SETUP_G1_LAGRANGE, BLSFieldElement, bit_reversal_permutation, \
    compute_roots_of_unity
from eth2spec.utils import bls
from py_ecc.bls.typing import G1Uncompressed
from remerkleable.basic import uint64

G1 = G1Uncompressed

BYTES_PER_FIELD_ELEMENT = 32
# we reversed the trusted setup here as np uses a biggest element first approach
GLOBAL_PARAMETERS: List[G1] = list(bls.bytes48_to_G1(g) for g in bit_reversal_permutation(KZG_SETUP_G1_LAGRANGE))
ROOTS_OF_UNITY: List[BLSFieldElement] = list(bit_reversal_permutation(compute_roots_of_unity(uint64(4096))))
BLS_MODULUS = eth2spec.eip7594.mainnet.BLS_MODULUS