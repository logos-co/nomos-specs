from dataclasses import dataclass
from itertools import batched, chain
from typing import List, Sequence, Tuple
from hashlib import blake2b

from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof, BLSFieldElement

from da.common import ChunksMatrix, Chunk, Row, Column
from da.kzg_rs import kzg, rs
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY, BLS_MODULUS, BYTES_PER_FIELD_ELEMENT
from da.kzg_rs.poly import Polynomial


@dataclass
class DAEncoderParams:
    column_count: int
    bytes_per_chunk: int


@dataclass
class EncodedData:
    data: bytes
    chunked_data: ChunksMatrix
    extended_matrix: ChunksMatrix
    row_commitments: List[Commitment]
    row_proofs: List[List[Proof]]
    column_commitments: List[Commitment]
    aggregated_column_commitment: Commitment
    aggregated_column_proofs: List[Proof]


class DAEncoder:
    def __init__(self, params: DAEncoderParams):
        # we can only encode up to 31 bytes per element which fits without problem in a 32 byte element
        assert params.bytes_per_chunk < BYTES_PER_FIELD_ELEMENT
        self.params = params

    def _chunkify_data(self, data: bytes) -> ChunksMatrix:
        size: int = self.params.column_count * self.params.bytes_per_chunk
        return ChunksMatrix(
            Row(Chunk(int.from_bytes(chunk, byteorder="big").to_bytes(length=BYTES_PER_FIELD_ELEMENT))
                for chunk in batched(b, self.params.bytes_per_chunk)
            )
            for b in batched(data, size)
        )

    def _compute_row_kzg_commitments(self, matrix: ChunksMatrix) -> List[Tuple[Polynomial, Commitment]]:
        return [
            kzg.bytes_to_commitment(
                row.as_bytes(),
                GLOBAL_PARAMETERS,
            )
            for row in matrix
        ]

    def _rs_encode_rows(self, chunks_matrix: ChunksMatrix) -> ChunksMatrix:
        def __rs_encode_row(row: Row) -> Row:
            polynomial = kzg.bytes_to_polynomial(row.as_bytes())
            return Row(
                Chunk(BLSFieldElement.to_bytes(
                    x,
                    # fixed to 32 bytes as bls_field_elements are 32bytes (256bits) encoded
                    length=32, byteorder="big"
                )) for x in rs.encode(polynomial, 2, ROOTS_OF_UNITY)
            )
        return ChunksMatrix(__rs_encode_row(row) for row in chunks_matrix)

    @staticmethod
    def _compute_rows_proofs(
        chunks_matrix: ChunksMatrix,
        polynomials: Sequence[Polynomial],
        row_commitments: Sequence[Commitment]
    ) -> List[List[Proof]]:
        proofs = []
        for row, poly, commitment in zip(chunks_matrix, polynomials, row_commitments):
            proofs.append(
                [
                    kzg.generate_element_proof(i, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
                    for i in range(len(row))
                ]
            )
        return proofs

    def _compute_column_kzg_commitments(self, chunks_matrix: ChunksMatrix) -> List[Tuple[Polynomial, Commitment]]:
        return self._compute_row_kzg_commitments(chunks_matrix.transposed())

    @staticmethod
    def _compute_aggregated_column_commitment(
        chunks_matrix: ChunksMatrix, column_commitments: Sequence[Commitment]
    ) -> Tuple[Polynomial, Commitment]:
        data = bytes(chain.from_iterable(
            DAEncoder.hash_column_and_commitment(column, commitment)
            for column, commitment in zip(chunks_matrix.columns, column_commitments)
        ))
        return kzg.bytes_to_commitment(data, GLOBAL_PARAMETERS)

    @staticmethod
    def _compute_aggregated_column_proofs(
            polynomial: Polynomial,
            column_commitments: Sequence[Commitment],
    ) -> List[Proof]:
        return [
            kzg.generate_element_proof(i, polynomial, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
            for i in range(len(column_commitments))
        ]

    def encode(self, data: bytes) -> EncodedData:
        chunks_matrix = self._chunkify_data(data)
        row_polynomials, row_commitments = zip(*self._compute_row_kzg_commitments(chunks_matrix))
        extended_matrix = self._rs_encode_rows(chunks_matrix)
        row_proofs = self._compute_rows_proofs(extended_matrix, row_polynomials, row_commitments)
        column_polynomials, column_commitments = zip(*self._compute_column_kzg_commitments(extended_matrix))
        aggregated_column_polynomial, aggregated_column_commitment = (
            self._compute_aggregated_column_commitment(extended_matrix, column_commitments)
        )
        aggregated_column_proofs = self._compute_aggregated_column_proofs(
            aggregated_column_polynomial, column_commitments
        )
        result = EncodedData(
            data,
            chunks_matrix,
            extended_matrix,
            row_commitments,
            row_proofs,
            column_commitments,
            aggregated_column_commitment,
            aggregated_column_proofs
        )
        return result

    @staticmethod
    def hash_column_and_commitment(column: Column, commitment: Commitment) -> bytes:
        return (
            # digest size must be 31 bytes as we cannot encode 32 without risking overflowing the BLS_MODULUS
            int.from_bytes(blake2b(column.as_bytes() + bytes(commitment), digest_size=31).digest())
        ).to_bytes(32, byteorder="big")
