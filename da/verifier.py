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
    def _verify_column(
            column: Column,
            column_commitment: Commitment,
            aggregated_column_commitment: Commitment,
            aggregated_column_proof: Proof,
            index: int
    ) -> bool:
        # 1. compute commitment for column
        _, computed_column_commitment = kzg.bytes_to_commitment(column.as_bytes(), GLOBAL_PARAMETERS)
        # 2. If computed column commitment != column commitment, fail
        if column_commitment != computed_column_commitment:
            return False
        # 3. compute column hash
        column_hash = DAEncoder.hash_commitment_blake2b31(column_commitment)
        # 4. Check proof with commitment and proof over the aggregated column commitment
        chunk = BLSFieldElement.from_bytes(column_hash)
        return kzg.verify_element_proof(
            combined_eval_point,
            combined_commitment,
            blob.combined_column_proof,
            blob.column_idx,
            ROOTS_OF_UNITY
        )
