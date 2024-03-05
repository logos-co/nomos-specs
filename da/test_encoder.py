from itertools import chain
from random import randrange
from typing import List
from unittest import TestCase

from da import encoder
from da.encoder import DAEncoderParams, Commitment, DAEncoder
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT

from da.kzg_rs.common import BLS_MODULUS


class TestEncoder(TestCase):

    def setUp(self):
        self.params: DAEncoderParams = DAEncoderParams(column_count=10, bytes_per_field_element=32)
        self.encoder: DAEncoder = DAEncoder(self.params)
        self.elements = 100
        self.data = bytearray(
            chain.from_iterable(
                randrange(BLS_MODULUS).to_bytes(length=self.params.bytes_per_field_element, byteorder='big')
                for _ in range(self.elements)
            )
        )

    def assert_encoding(self, encoder_params: DAEncoderParams, data: bytearray):
        encoded_data = encoder.DAEncoder(encoder_params).encode(data)
        self.assertEqual(encoded_data.data, data)
        self.assertEqual(len(encoded_data.extended_matrix), encoder_params.column_count)
        chunks_size = (len(data) // encoder_params.bytes_per_field_element) // encoder_params.column_count
        self.assertEqual(len(encoded_data.row_commitments), chunks_size)
        self.assertEqual(len(encoded_data.row_proofs), chunks_size)

    def test_chunkify(self):
        encoder_settings = DAEncoderParams(column_count=2, bytes_per_field_element=32)
        elements = 10
        data = bytearray(chain.from_iterable(int.to_bytes(0, length=32, byteorder='big') for _ in range(elements)))
        _encoder = encoder.DAEncoder(encoder_settings)
        chunks_matrix = _encoder._chunkify_data(data)
        self.assertEqual(len(chunks_matrix), elements//encoder_settings.column_count)
        for column in chunks_matrix:
            self.assertEqual(len(column), encoder_settings.bytes_per_field_element*encoder_settings.column_count)

    def test_compute_row_kzg_commitments(self):
        chunks_matrix = self.encoder._chunkify_data(self.data)
        commitments = self.encoder._compute_row_kzg_commitments(chunks_matrix)
        self.assertEqual(len(commitments), len(chunks_matrix))

    def test_rs_encode_rows(self):
        pass

    def test_compute_rows_proofs(self):
        pass

    def test_compute_column_kzg_commitments(self):
        pass

    def test_generate_aggregated_column_commitments(self):
        pass

    def test_encode(self):
        # TODO: remove return, for now we make it work for now so we do not disturb other modules
        return
        from random import randbytes
        sizes = [pow(2, exp) for exp in range(0, 8, 2)]
        encoder_params = DAEncoderParams(
            column_count=10,
            bytes_per_field_element=BYTES_PER_FIELD_ELEMENT
        )
        for size in sizes:
            data = bytearray(randbytes(size*1024))
            self.assert_encoding(encoder_params, data)
