from itertools import chain, batched
from random import randbytes
from unittest import TestCase

from da import encoder
from da.common import Column
from da.kzg_rs.bdfg_proving import derive_challenge, compute_combined_polynomial
from da.encoder import DAEncoderParams, DAEncoder
from da.verifier import DAVerifier, DAShare
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT, BLSFieldElement

from da.kzg_rs.common import ROOTS_OF_UNITY
from da.kzg_rs import kzg, rs


class TestEncoder(TestCase):
    def setUp(self):
        self.params: DAEncoderParams = DAEncoderParams(column_count=16, bytes_per_chunk=31)
        self.encoder: DAEncoder = DAEncoder(self.params)
        self.elements = 32
        self.data = bytearray(
            chain.from_iterable(
                randbytes(self.params.bytes_per_chunk)
                for _ in range(self.elements)
            )
        )

    def assert_encoding(self, encoder_params: DAEncoderParams, data: bytes):
        encoded_data = encoder.DAEncoder(encoder_params).encode(data)
        self.assertEqual(encoded_data.data, data)
        extended_factor = 2
        column_count = encoder_params.column_count*extended_factor
        columns_len = len(list(encoded_data.extended_matrix.columns))
        self.assertEqual(columns_len, column_count)
        chunks_size = (len(data) // encoder_params.bytes_per_chunk) // encoder_params.column_count
        self.assertEqual(len(encoded_data.row_commitments), chunks_size)

        verifier = DAVerifier()
        # verify columns
        for idx, (column, column_proof) in enumerate(zip(encoded_data.extended_matrix.columns, encoded_data.combined_column_proofs)):
            share = DAShare(
                column=Column(column),
                column_idx=idx,
                combined_column_proof=column_proof,
                row_commitments=encoded_data.row_commitments
            )
            verifier.verify(share)



    def test_chunkify(self):
        encoder_settings = DAEncoderParams(column_count=2, bytes_per_chunk=31)
        elements = 10
        data = bytes(chain.from_iterable(int.to_bytes(0, length=31, byteorder='big') for _ in range(elements)))
        _encoder = encoder.DAEncoder(encoder_settings)
        chunks_matrix = _encoder._chunkify_data(data)
        self.assertEqual(len(chunks_matrix), elements//encoder_settings.column_count)
        for row in chunks_matrix:
            self.assertEqual(len(row), encoder_settings.column_count)
            self.assertEqual(len(row[0]), 32)

    def test_compute_row_kzg_commitments(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        polynomials, commitments = zip(*self.encoder._compute_row_kzg_commitments(chunks_matrix))
        self.assertEqual(len(commitments), len(chunks_matrix))
        self.assertEqual(len(polynomials), len(chunks_matrix))

    def test_rs_encode_rows(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        extended_chunks_matrix = self.encoder._rs_encode_rows(chunks_matrix)
        for r1, r2 in zip(chunks_matrix, extended_chunks_matrix):
            self.assertEqual(len(r1), len(r2)//2)
            r2 = [BLSFieldElement.from_bytes(x) for x in r2]
            poly_1 = kzg.bytes_to_polynomial(r1.as_bytes())
            # we check against decoding so we now the encoding was properly done
            poly_2 = rs.decode(r2, ROOTS_OF_UNITY, len(poly_1))
            self.assertEqual(poly_1, poly_2)


    def test_generate_combined_column_proofs(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        row_polynomials, row_commitments = zip(*self.encoder._compute_row_kzg_commitments(chunks_matrix))
        h = derive_challenge(row_commitments)
        combined_poly = compute_combined_polynomial(row_polynomials, h)
        proofs = self.encoder._compute_combined_column_proofs(combined_poly)
        expected_extended_columns = self.params.column_count * 2
        self.assertEqual(len(proofs), expected_extended_columns)

    def test_encode(self):
        from random import randbytes
        sizes = [pow(2, exp) for exp in range(4, 8, 2)]
        encoder_params = DAEncoderParams(
            column_count=8,
            bytes_per_chunk=31
        )
        for size in sizes:
            data = bytes(
                chain.from_iterable(
                    randbytes(encoder_params.bytes_per_chunk)
                    for _ in range(size*encoder_params.column_count)
                )
            )
            self.assert_encoding(encoder_params, data)