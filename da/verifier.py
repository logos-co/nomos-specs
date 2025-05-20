from dataclasses import dataclass
from typing import List, Sequence, Set
from hashlib import blake2b
from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)

import da.common
from da.common import Column, Chunk, BlobId, build_blob_id
from da.kzg_rs import kzg
from da.kzg_rs.common import ROOTS_OF_UNITY, GLOBAL_PARAMETERS, BLS_MODULUS

# Domain separation tag
_DST = b"NOMOS_DA_V1"

@dataclass
class DAShare:
    column: Column
    column_idx: int
    combined_column_proof: Proof
    row_commitments: List[Commitment]

    def blob_id(self) -> BlobId:
        return build_blob_id(self.row_commitments)

class DAVerifier:

    @staticmethod
    def _derive_challenge(row_commitments: List[Commitment]) -> BLSFieldElement:
        """
        Derive a Fiat–Shamir challenge scalar h from the row commitments:
          h = BLAKE2b-31( DST || bytes(com1) || bytes(com2) || ... )
        """
        h = blake2b(digest_size=31)
        h.update(_DST)
        for com in row_commitments:
            h.update(bytes(com))
        digest31 = h.digest()  # 31 bytes
        # pad to 32 bytes for field element conversion
        padded = digest31 + b'\x00'
        return BLSFieldElement.from_bytes(padded)

    @staticmethod
    def verify(blob: DAShare) -> bool:
        """
        Verifies that blob.column.chunks at index blob.column_idx is consistent
        with the row commitments and the single column proof.

        Returns True if verification succeeds, False otherwise.
        """
        # 1. Derive challenge
        h = DAVerifier._derive_challenge(blob.row_commitments)
        # 2. Reconstruct combined commitment: com_C = sum_{i=0..l-1} h^i * row_commitments[i]
        com_C = blob.row_commitments[0]
        power = h
        for com in blob.row_commitments[1:]:
            com_C = com_C + com * int(power)
            power = power * h

        # 3. Compute combined evaluation v = sum_{i=0..l-1} (h^i * column_data[i])
        v = BLSFieldElement(0)
        power = BLSFieldElement(1)
        for chunk in blob.column.chunks:
            x = BLSFieldElement(int.from_bytes(bytes(chunk), byteorder="big"))
            v = v + x * power
            power = power * h
        # 4. Verify the single KZG proof for evaluation at point w^{column_idx}
        return kzg.verify_element_proof(v,com_C,blob.combined_column_proof,blob.column_idx,ROOTS_OF_UNITY)
