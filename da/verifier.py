from dataclasses import dataclass
from typing import List, Sequence, Set
from hashlib import blake2b
from eth2spec.utils import bls
from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)

import da.common
from da.common import Column, Chunk, BlobId, build_blob_id, derive_challenge
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
    def verify(blob: DAShare) -> bool:
        """
        Verifies that blob.column.chunks at index blob.column_idx is consistent
        with the row commitments and the single column proof.

        Returns True if verification succeeds, False otherwise.
        """
        # 1. Derive challenge
        h = derive_challenge(blob.row_commitments)
        # 2. Reconstruct combined commitment: combined_commitment = sum_{i=0..l-1} h^i * row_commitments[i]
        combined_commitment = blob.row_commitments[0]
        power = h
        for com in blob.row_commitments[1:]:
            combined_commitment = bls.add(combined_commitment,bls.multiply(com, power))
            power = power * h

        # 3. Compute combined evaluation v = sum_{i=0..l-1} (h^i * column_data[i])
        combined_eval_point = BLSFieldElement(0)
        power = BLSFieldElement(1)
        for data in blob.column.chunks:
            chunk = BLSFieldElement(int.from_bytes(bytes(data), byteorder="big"))
            combined_eval_point = combined_eval_point + chunk * power
            power = power * h
        # 4. Verify the single KZG proof for evaluation at point w^{column_idx}
        return kzg.verify_element_proof(combined_eval_point,combined_commitment,blob.combined_column_proof,blob.column_idx,ROOTS_OF_UNITY)
