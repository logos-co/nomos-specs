from dataclasses import dataclass
from hashlib import sha3_256
from typing import List, Optional, Sequence

from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)
from itertools import batched

from da.common import Column, Chunk, Attestation
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import ROOTS_OF_UNITY, GLOBAL_PARAMETERS, BLS_MODULUS


@dataclass
class DABlob:
    index: int
    column: Column
    column_commitment: Commitment
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof
    rows_commitments: List[Commitment]
    rows_proofs: List[Proof]


class DAVerifier:
    def __init__(self):
        pass

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
        column_hash = DAEncoder.hash_column_and_commitment(column, column_commitment)
        # 4. Check proof with commitment and proof over the aggregated column commitment
        chunk = BLSFieldElement.from_bytes(column_hash)
        return kzg.verify_element_proof(
            chunk, aggregated_column_commitment, aggregated_column_proof, index, ROOTS_OF_UNITY
        )

    @staticmethod
    def _verify_chunk(chunk: Chunk, commitment: Commitment, proof: Proof, index: int) -> bool:
        chunk = BLSFieldElement.from_bytes((int.from_bytes(chunk) % BLS_MODULUS).to_bytes())
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

    def _build_attestation(self, _blob: DABlob) -> Attestation:
        return Attestation()

    @staticmethod
    def verify(blob: DABlob) -> Optional[Attestation]:
        is_column_verified = DAVerifier._verify_column(
            blob.column, blob.aggregated_column_commitment, blob.aggregated_column_proof, blob.index
        )
        if not is_column_verified:
            return
        are_chunks_verified = DAVerifier._verify_chunks(
            blob.column, blob.rows_commitments, blob.rows_proofs, blob.index
        )
        if not are_chunks_verified:
            return
        return DAVerifier._build_attestation(blob)
