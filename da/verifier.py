from dataclasses import dataclass
from typing import List

from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)

from da.common import Column, BlobId, build_blob_id
from da.kzg_rs import kzg
from da.kzg_rs.bdfg_proving import combine_commitments, derive_challenge, compute_combined_evaluation
from da.kzg_rs.common import ROOTS_OF_UNITY

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
        Verifies that blob.column at index blob.column_idx is consistent
        with the row commitments and the combined column proof.

        Returns True if verification succeeds, False otherwise.
        """
        # 1. Derive challenge
        h = derive_challenge(blob.row_commitments)
        # 2. Reconstruct combined commitment: combined_commitment = sum_{i=0..l-1} h^i * row_commitments[i]
        combined_commitment = combine_commitments(blob.row_commitments, h)
        # 3. Compute combined evaluation v = sum_{i=0..l-1} (h^i * column_data[i])
        combined_eval_point = compute_combined_evaluation(blob.column, h)
        # 4. Verify the single KZG proof for evaluation at point w^{column_idx}
        return kzg.verify_element_proof(
            combined_eval_point,
            combined_commitment,
            blob.combined_column_proof,
            blob.column_idx,
            ROOTS_OF_UNITY
        )
