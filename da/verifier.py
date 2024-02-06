from dataclasses import dataclass
from typing import List, Optional
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
    BYTES_PER_CELL as BYTES_PER_CHUNK
)
from itertools import batched


@dataclass
class DABlob:
    # this should be removed, but for now it shows the purpose
    index: int
    column: bytearray
    column_commitment: Commitment
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof
    rows_commitments: List[Commitment]
    rows_proofs: List[Proof]


@dataclass
class Attestation:
    pass


class DAVerifier:
    def __init__(self):
        pass

    @staticmethod
    def _verify_column(
            column: bytearray,
            column_commitment: Commitment,
            aggregated_column_commitment: Commitment,
            aggregated_column_proof: Proof,
            # this is temporary and should be removed
            index: int
    ) -> bool:

        # 1. compute commitment for column
        # 2. If computed column commitment != column commitment, fail
        # 3. compute column hash
        column_hash: bytearray = bytearray(hash(column))
        # 4. Check proof with commitment and proof over the aggregated column commitment
        pass

    @staticmethod
    def _verify_chunk(chunk: bytearray, commitment: Commitment, proof: Proof) -> bool:
        pass

    @staticmethod
    def _verify_chunks(
            chunks: List[bytearray],
            commitments: List[Commitment],
            proofs: List[Proof]
    ) -> bool:
        for chunk, commitment, proof in zip(chunks, commitments, proofs):
            if not DAVerifier._verify_chunk(chunk, commitment, proof):
                return False
        return True

    def _build_attestation(self, _blob: DABlob) -> Attestation:
        return Attestation()

    @staticmethod
    def verify(self, blob: DABlob) -> Optional[Attestation]:
        is_column_verified = DAVerifier._verify_column(
            blob.column, blob.aggregated_column_commitment, blob.aggregated_column_proof, blob.index
        )
        if not is_column_verified:
            return
        chunks = batched(blob.column, BYTES_PER_CHUNK)
        are_chunks_verified = DAVerifier._verify_chunks(
            chunks, blob.rows_commitments, blob.rows_proofs
        )
        if not are_chunks_verified:
            return
        return self._build_attestation(blob)
