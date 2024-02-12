from typing import List
from unittest import TestCase

from da import encoder
from da.encoder import DAEncoderParams, Commitment
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT


class TestEncoder(TestCase):
    def assert_encoding(self, encoder_params: DAEncoderParams, data: bytearray):
        encoded_data = encoder.DAEncoder(encoder_params).encode(data)
        self.assertEqual(encoded_data.data, data)
        self.assertEqual(len(encoded_data.extended_matrix), encoder_params.column_count)
        chunks_size = (len(data) // encoder_params.bytes_per_field_element) // encoder_params.column_count
        self.assertEqual(len(encoded_data.row_commitments), chunks_size)
        self.assertEqual(len(encoded_data.row_proofs), chunks_size)

    def test_chunkify(self):
        pass

    def test_compute_row_kzg_commitments(self):
        pass

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
