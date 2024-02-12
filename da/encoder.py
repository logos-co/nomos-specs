from dataclasses import dataclass
from typing import List
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof
from itertools import batched, chain, repeat
from da.common import ChunksMatrix, Row, Chunk


@dataclass
class DAEncoderParams:
    column_count: int
    bytes_per_field_element: int


@dataclass
class EncodedData:
    data: bytearray
    extended_matrix: ChunksMatrix
    row_commitments: List[Commitment]
    row_proofs: List[List[Proof]]
    column_commitments: List[Commitment]
    aggregated_column_commitment: Commitment
    aggregated_column_proofs: List[Proof]


class DAEncoder:
    def __init__(self, params: DAEncoderParams):
        self.params = params

    def _chunkify_data(self, data: bytearray) -> ChunksMatrix:
        chunks = [Chunk(b) for b in batched(data, self.params.bytes_per_field_element)]
        extra = len(chunks) % self.params.column_count
        if extra > 0:
            chunks.extend(Chunk(Chunk.default_bytes()) for _ in range(self.params.column_count - extra))
        rows = list(batched(chunks, self.params.column_count))
        return ChunksMatrix(rows)

    def _compute_row_kzg_commitments(self, rows: List[bytearray]) -> List[Commitment]:
        ...

    def _rs_encode_rows(self, chunks_matrix: ChunksMatrix) -> ChunksMatrix:
        ...

    def _compute_rows_proofs(self, chunks_matrix: ChunksMatrix, row_commitments: List[Commitment]) -> List[List[Proof]]:
        ...

    def _compute_column_kzg_commitments(self, chunks_matrix: ChunksMatrix) -> List[Commitment]:
        ...

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

    def encode(self, data: bytearray) -> EncodedData:
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
