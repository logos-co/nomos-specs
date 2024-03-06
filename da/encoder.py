from dataclasses import dataclass
from itertools import batched, chain
from typing import List, Sequence, Tuple
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof, BLSFieldElement

from da.common import ChunksMatrix, Chunk, Row
from da.kzg_rs import kzg, rs, poly
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY
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
            Row([bytes(chunk) for chunk in batched(b, self.params.bytes_per_field_element)])
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

    def _compute_rows_proofs(
            self,
            chunks_matrix: ChunksMatrix,
            polynomials: Sequence[Polynomial],
            row_commitments: Sequence[Commitment]) -> List[List[Proof]]:
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

    def _compute_aggregated_column_commitments(
            self, chunks_matrix: ChunksMatrix, column_commitments: List[Commitment]
    ) -> Commitment:
        ...

    def _compute_aggregated_column_proofs(
            self,
            chunks_matrix: ChunksMatrix,
            aggregated_column_commitment: Commitment
    ) -> List[Proof]:
        ...

    def encode(self, data: bytes) -> EncodedData:
        chunks_matrix = self._chunkify_data(data)
        row_commitments = self._compute_row_kzg_commitments(chunks_matrix)
        extended_matrix = self._rs_encode_rows(chunks_matrix)
        row_proofs = self._compute_rows_proofs(extended_matrix, row_commitments)
        column_commitments = self._compute_column_kzg_commitments(extended_matrix)
        aggregated_column_commitment = self._compute_aggregated_column_commitments(extended_matrix, column_commitments)
        aggregated_column_proofs = self._compute_aggregated_column_proofs(extended_matrix, aggregated_column_commitment)
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
