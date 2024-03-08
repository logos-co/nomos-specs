from dataclasses import dataclass
from itertools import batched, chain
from typing import List, Sequence, Tuple
from hashlib import sha3_256

from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof, BLSFieldElement

from da.common import ChunksMatrix, Chunk, Row, Column
from da.kzg_rs import kzg, rs
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY, BLS_MODULUS
from da.kzg_rs.poly import Polynomial


@dataclass
class DAEncoderParams:
    column_count: int
    bytes_per_field_element: int


@dataclass
class EncodedData:
    data: bytes
    extended_matrix: ChunksMatrix
    row_commitments: List[Commitment]
    row_proofs: List[List[Proof]]
    column_commitments: List[Commitment]
    aggregated_column_commitment: Commitment
    aggregated_column_proofs: List[Proof]


class DAEncoder:
    def __init__(self, params: DAEncoderParams):
        self.params = params

    def _chunkify_data(self, data: bytes) -> ChunksMatrix:
        size: int = self.params.column_count * self.params.bytes_per_field_element
        return ChunksMatrix(
            Row(Chunk(bytes(chunk)) for chunk in batched(b, self.params.bytes_per_field_element))
            for b in batched(data, size)
        )

    @staticmethod
    def _compute_row_kzg_commitments(matrix: ChunksMatrix) -> List[Tuple[Polynomial, Commitment]]:
        return [kzg.bytes_to_commitment(row.as_bytes(), GLOBAL_PARAMETERS) for row in matrix]

    def _rs_encode_rows(self, chunks_matrix: ChunksMatrix) -> ChunksMatrix:
        def __rs_encode_row(row: Row) -> Row:
            polynomial = kzg.bytes_to_polynomial(row.as_bytes())
            return Row(
                Chunk(BLSFieldElement.to_bytes(
                    x,
                    length=self.params.bytes_per_field_element, byteorder="big"
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
            DAEncoder._hash_column_and_commitment(column, commitment)
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
            extended_matrix,
            row_commitments,
            row_proofs,
            column_commitments,
            aggregated_column_commitment,
            aggregated_column_proofs
        )
        return result

    @staticmethod
    def _hash_column_and_commitment(column: Column, commitment: Commitment) -> bytes:
        # TODO: Check correctness of bytes to blsfieldelement using modulus over the hash
        return (
                int.from_bytes(sha3_256(column.as_bytes() + bytes(commitment)).digest()) % BLS_MODULUS
        ).to_bytes(32, byteorder="big")
