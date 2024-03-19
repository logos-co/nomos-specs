from itertools import chain, batched
from random import randrange, randbytes
from unittest import TestCase

from eth2spec.deneb.mainnet import bytes_to_bls_field

from da import encoder
from da.encoder import DAEncoderParams, DAEncoder
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT, BLSFieldElement

from da.kzg_rs.common import BLS_MODULUS, ROOTS_OF_UNITY
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
        self.assertEqual(len(encoded_data.row_proofs), chunks_size)
        self.assertEqual(len(encoded_data.row_proofs[0]), column_count)
        self.assertIsNotNone(encoded_data.aggregated_column_commitment)
        self.assertEqual(len(encoded_data.aggregated_column_proofs), columns_len)

        # verify rows
        for row, proofs, commitment in zip(encoded_data.extended_matrix, encoded_data.row_proofs, encoded_data.row_commitments):
            for i, (chunk, proof) in enumerate(zip(row, proofs)):
                self.assertTrue(
                    kzg.verify_element_proof(bytes_to_bls_field(chunk), commitment, proof, i, ROOTS_OF_UNITY)
                )

        # verify column aggregation
        for i, (column, proof) in enumerate(zip(encoded_data.extended_matrix.columns, encoded_data.aggregated_column_proofs)):
            data = DAEncoder.hash_column_and_commitment(column, commitment)
            kzg.verify_element_proof(
                bytes_to_bls_field(data),
                encoded_data.aggregated_column_commitment,
                proof,
                i,
                ROOTS_OF_UNITY
            )

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

    def test_compute_rows_proofs(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        polynomials, commitments = zip(*self.encoder._compute_row_kzg_commitments(chunks_matrix))
        extended_chunks_matrix = self.encoder._rs_encode_rows(chunks_matrix)
        original_proofs = self.encoder._compute_rows_proofs(chunks_matrix, polynomials, commitments)
        extended_proofs = self.encoder._compute_rows_proofs(extended_chunks_matrix, polynomials, commitments)
        # check original sized matrix
        for row, poly, commitment, proofs in zip(chunks_matrix, polynomials, commitments, original_proofs):
            self.assertEqual(len(proofs), len(row))
            for i, chunk in enumerate(row):
                self.assertTrue(kzg.verify_element_proof(BLSFieldElement.from_bytes(chunk), commitment, proofs[i], i, ROOTS_OF_UNITY))
        # check extended matrix
        for row, poly, commitment, proofs in zip(extended_chunks_matrix, polynomials, commitments, extended_proofs):
            for i, chunk in enumerate(row):
                self.assertTrue(kzg.verify_element_proof(BLSFieldElement.from_bytes(chunk), commitment, proofs[i], i, ROOTS_OF_UNITY))

    def test_compute_column_kzg_commitments(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        polynomials, commitments = zip(*self.encoder._compute_column_kzg_commitments(chunks_matrix))
        self.assertEqual(len(commitments), len(chunks_matrix[0]))
        self.assertEqual(len(polynomials), len(chunks_matrix[0]))

    def test_generate_aggregated_column_commitments(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        _, column_commitments = zip(*self.encoder._compute_column_kzg_commitments(chunks_matrix))
        poly, commitment = self.encoder._compute_aggregated_column_commitment(chunks_matrix, column_commitments)
        self.assertIsNotNone(poly)
        self.assertIsNotNone(commitment)

    def test_generate_aggregated_column_proofs(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        _, column_commitments = zip(*self.encoder._compute_column_kzg_commitments(chunks_matrix))
        poly, _ = self.encoder._compute_aggregated_column_commitment(chunks_matrix, column_commitments)
        proofs = self.encoder._compute_aggregated_column_proofs(poly, column_commitments)
        self.assertEqual(len(proofs), len(column_commitments))

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
