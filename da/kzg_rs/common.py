from typing import List, Tuple

import eth2spec.eip7594.mainnet
from py_ecc.bls.typing import G1Uncompressed, G2Uncompressed

from da.kzg_rs.roots import compute_roots_of_unity
from da.kzg_rs.trusted_setup import generate_setup

G1 = G1Uncompressed
G2 = G2Uncompressed


BYTES_PER_FIELD_ELEMENT = 32
BLS_MODULUS = eth2spec.eip7594.mainnet.BLS_MODULUS
PRIMITIVE_ROOT: int = 7
GLOBAL_PARAMETERS: List[G1]
GLOBAL_PARAMETERS_G2: List[G2]
# secret is fixed but this should come from a different synchronization protocol
GLOBAL_PARAMETERS, GLOBAL_PARAMETERS_G2 = map(list, generate_setup(4096, 8, 1987))
ROOTS_OF_UNITY: Tuple[int] = compute_roots_of_unity(
    PRIMITIVE_ROOT, 4096, BLS_MODULUS
)
