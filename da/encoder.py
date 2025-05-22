from dataclasses import dataclass
from itertools import batched
from typing import List, Sequence, Tuple
from hashlib import blake2b

from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof, BLSFieldElement

from da.common import ChunksMatrix, Chunk, Row, derive_challenge
from da.kzg_rs import kzg, rs
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY, BYTES_PER_FIELD_ELEMENT, BLS_MODULUS
from da.kzg_rs.poly import Polynomial

# Domain separation tag
_DST = b"NOMOS_DA_V1"

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
    combined_column_proofs: List[Proof]


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
    def _combined_polynomial(
        polys: Sequence[Polynomial], h: BLSFieldElement
    ) -> Polynomial:
        combined = Polynomial([0], BLS_MODULUS)
        h_int = int(h)  # raw integer challenge
        int_pow = 1
        for poly in polys:
            combined = combined + (poly * int_pow)
            int_pow = (int_pow * h_int) % BLS_MODULUS
        return combined

    def _compute_combined_column_proofs(self, combined_poly: Polynomial) -> List[Proof]:
        total_cols = self.params.column_count * 2
        return [
            kzg.generate_element_proof(j, combined_poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
            for j in range(total_cols)
        ]

    def encode(self, data: bytes) -> EncodedData:
        chunks_matrix = self._chunkify_data(data)
        row_polynomials, row_commitments = zip(*self._compute_row_kzg_commitments(chunks_matrix))
        extended_matrix = self._rs_encode_rows(chunks_matrix)
        h = derive_challenge(row_commitments)
        combined_poly = self._combined_polynomial(row_polynomials, h)
        combined_column_proofs = self._compute_combined_column_proofs(combined_poly)
        result = EncodedData(
            data,
            chunks_matrix,
            extended_matrix,
            row_commitments,
            combined_column_proofs
        )
        return result
