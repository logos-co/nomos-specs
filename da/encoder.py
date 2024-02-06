from dataclasses import dataclass
from typing import List
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof


class DAEncoderParams:
    column_count: int
    element_size: int


@dataclass
class EncodedData:
    data: bytearray
    columns: List[bytearray]
    row_commitments: List[Commitment]
    row_proofs: List[List[Proof]]
    column_commitments: List[Commitment]
    column_proofs: List[Proof]
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof


class DAEncoder:
    def __init__(self, params: DAEncoderParams):
        self.params = params

    def _chunkify_data(self) -> List[bytearray]:
        ...

    def _compute_row_kzg_commitments(self, rows: List[bytearray]) -> List[Commitment]:
        ...

    def _rs_encode_rows(self, rows: List[bytearray]) -> List[bytearray]:
        ...

    def _compute_rows_proofs(self, rows: List[bytearray], row_commitments: List[Commitment]) -> List[List[Proof]]:
        ...

    def _compute_column_kzg_commitments(self, rows: List[bytearray]) -> List[Commitment]:
        ...

    def _generate_aggregated_column_commitments(
            self, rows: List[bytearray], column_commitments: List[Commitment]
    ) -> Commitment:
        ...

    def encode(self, data: bytearray) -> EncodedData:
        rows = self._chunkify_data()
        row_commitments = self._compute_row_kzg_commitments(rows)
        encoded_rows = self._rs_encode_rows(rows)
        row_proofs = self._compute_rows_proofs(encoded_rows, row_commitments)
        column_commitments = self._compute_column_kzg_commitments(encoded_rows)
        aggregated_column_commitment = self._generate_aggregated_column_commitments(encoded_rows, column_commitments)
        result = EncodedData(
            data,
            row_commitments,
            row_proofs,
            column_commitments,
            aggregated_column_commitment

        )
        return result
