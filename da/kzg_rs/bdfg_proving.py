from hashlib import blake2b
from typing import List, Sequence

from da.common import Chunk
from da.kzg_rs.common import BLS_MODULUS

from eth2spec.eip7594.mainnet import BLSFieldElement, KZGCommitment as Commitment
from eth2spec.utils import bls

from da.kzg_rs.poly import Polynomial


def derive_challenge(row_commitments: List[Commitment]) -> BLSFieldElement:
    """
    Derive a Fiat–Shamir challenge scalar h from the row commitments:
        h = BLAKE2b-31( DST || bytes(com1) || bytes(com2) || ... )
    """
    _DST = b"NOMOS_DA_V1"
    h = blake2b(digest_size=31)
    h.update(_DST)
    for com in row_commitments:
        h.update(bytes(com))
    digest31 = h.digest()  # 31 bytes
    # pad to 32 bytes for field element conversion
    padded = digest31 + b'\x00'
    return BLSFieldElement.from_bytes(padded)


def combine_commitments(row_commitments: List[Commitment], h: BLSFieldElement) -> Commitment:
    combined_commitment = bls.bytes48_to_G1(row_commitments[0])
    power = int(h) % BLS_MODULUS
    for commitment in row_commitments[1:]:
        commitment = bls.bytes48_to_G1(commitment)
        combined_commitment = bls.add(combined_commitment, bls.multiply(commitment, power))
        power = (power * int(h)) % BLS_MODULUS
    return bls.G1_to_bytes48(combined_commitment)


def compute_combined_polynomial(
        polys: Sequence[Polynomial], h: BLSFieldElement
    ) -> Polynomial:
        combined_polynomial = polys[0]
        h_int = int(h)  # raw integer challenge
        int_pow = 1
        for poly in polys[1:]:
            int_pow = (int_pow * h_int) % BLS_MODULUS
            combined_polynomial = combined_polynomial + Polynomial([int_pow * coeff for coeff in poly], BLS_MODULUS)
        return combined_polynomial

def compute_combined_evaluation(
        evals: Sequence[Chunk],
        h: BLSFieldElement
) -> BLSFieldElement:
    combined_eval_int = 0
    power_int = 1
    h_int = int(h) % BLS_MODULUS
    for chunk in evals:
        chunk_int = int.from_bytes(bytes(chunk), byteorder="big")
        combined_eval_int = (combined_eval_int + chunk_int * power_int) % BLS_MODULUS
        power_int = (power_int * h_int) % BLS_MODULUS
    return BLSFieldElement(combined_eval_int)