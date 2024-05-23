from dataclasses import dataclass
from hashlib import sha3_256
from typing import List, Optional, Sequence, Set, Dict

from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.eip7594.mainnet import (
    KZGCommitment as Commitment,
    KZGProof as Proof,
)

import da.common
from da.common import Column, Chunk, Attestation, BLSPrivateKey, BLSPublicKey, NomosDaG2ProofOfPossession as bls_pop
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import ROOTS_OF_UNITY, GLOBAL_PARAMETERS, BLS_MODULUS


@dataclass
class DABlob:
    column: Column
    column_commitment: Commitment
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof
    rows_commitments: List[Commitment]
    rows_proofs: List[Proof]

    def id(self) -> bytes:
        return da.common.build_attestation_message(self.aggregated_column_commitment, self.rows_commitments)

    def column_id(self) -> bytes:
        return sha3_256(self.column.as_bytes()).digest()


class DAVerifier:
    def __init__(self, sk: BLSPrivateKey, nodes_pks: List[BLSPublicKey]):
        self.attested_blobs: Dict[bytes, (bytes, Attestation)] = dict()
        self.sk = sk
        self.index = nodes_pks.index(bls_pop.SkToPk(self.sk))

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

    def _build_attestation(self, blob: DABlob) -> Attestation:
        hasher = sha3_256()
        hasher.update(bytes(blob.aggregated_column_commitment))
        for c in blob.rows_commitments:
            hasher.update(bytes(c))
        message = hasher.digest()
        return Attestation(signature=bls_pop.Sign(self.sk, message))

    def verify(self, blob: DABlob) -> Optional[Attestation]:
        blob_id = blob.id()
        if previous_attestation := self.attested_blobs.get(blob_id):
            column_id, attestation = previous_attestation
            # we already attested, is cached so we return it
            if column_id == blob.column_id():
                return attestation
            # we already attested and they are asking us to attest the same data different column
            # skip
            return None
        is_column_verified = DAVerifier._verify_column(
            blob.column,
            blob.column_commitment,
            blob.aggregated_column_commitment,
            blob.aggregated_column_proof,
            self.index
        )
        if not is_column_verified:
            return
        are_chunks_verified = DAVerifier._verify_chunks(
            blob.column, blob.rows_commitments, blob.rows_proofs, self.index
        )
        if not are_chunks_verified:
            return
        attestation = self._build_attestation(blob)
        self.attested_blobs[blob_id] = (blob.column_id(), attestation)
        return attestation
