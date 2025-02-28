from dataclasses import dataclass
from hashlib import sha3_256
from typing import List, Sequence, Set

from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)

import da.common
from da.common import Column, Chunk, BlobId
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import ROOTS_OF_UNITY, GLOBAL_PARAMETERS, BLS_MODULUS


@dataclass
class DABlob:
    column: Column
    column_idx: int
    column_commitment: Commitment
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof
    rows_commitments: List[Commitment]
    rows_proofs: List[Proof]

    def blob_id(self) -> bytes:
        return da.common.build_blob_id(self.aggregated_column_commitment, self.rows_commitments)

    def column_id(self) -> bytes:
        return sha3_256(self.column.as_bytes()).digest()


class DAVerifier:
    @staticmethod
    def _verify_column(
            column: Column,
            column_idx: int,
            column_commitment: Commitment,
            aggregated_column_commitment: Commitment,
            aggregated_column_proof: Proof,
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
            chunk, aggregated_column_commitment, aggregated_column_proof, column_idx, ROOTS_OF_UNITY
        )

    @staticmethod
    def _verify_chunk(chunk: Chunk, commitment: Commitment, proof: Proof, index: int) -> bool:
        chunk = BLSFieldElement(int.from_bytes(bytes(chunk)) % BLS_MODULUS)
        return kzg.verify_element_proof(chunk, commitment, proof, index, ROOTS_OF_UNITY)

    @staticmethod
    def _verify_chunks(
            chunks: Sequence[Chunk],
            commitments: Sequence[Commitment],
            proofs: Sequence[Proof],
            index: int
    ) -> bool:
        if not (len(chunks) == len(commitments) == len(proofs)):
            return False
        for chunk, commitment, proof in zip(chunks, commitments, proofs):
            if not DAVerifier._verify_chunk(chunk, commitment, proof, index):
                return False
        return True

    def verify(self, blob: DABlob) -> bool:
        """
        Verify the integrity of the given blob.

        This function must be idempotent. The implementer should ensure that
        repeated verification attempts do not result in inconsistent states.

        Args:
            blob (DABlob): The blob to verify.

        Returns:
            bool: True if the blob is verified successfully, False otherwise.
        """
        is_column_verified = DAVerifier._verify_column(
            blob.column,
            blob.column_idx,
            blob.column_commitment,
            blob.aggregated_column_commitment,
            blob.aggregated_column_proof,
        )
        if not is_column_verified:
            return False

        are_chunks_verified = DAVerifier._verify_chunks(
            blob.column, blob.rows_commitments, blob.rows_proofs, blob.column_idx
        )
        if not are_chunks_verified:
            return False

        # Ensure idempotency: Implementers should define how to avoid redundant verification.
        return True
