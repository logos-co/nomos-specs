from unittest import TestCase

from da.common import Column
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY
from da.test_encoder import TestEncoder
from da.verifier import DAVerifier, DAShare


class TestVerifier(TestCase):

    def setUp(self):
        self.verifier = DAVerifier()


    def test_verify(self):
        _ = TestEncoder()
        _.setUp()
        encoded_data = _.encoder.encode(_.data)
        for i, column in enumerate(encoded_data.extended_matrix.columns):
            verifier = DAVerifier()
            da_blob = DAShare(
                Column(column),
                i,
                encoded_data.combined_column_proofs[i],
                encoded_data.row_commitments,
            )
            self.assertIsNotNone(verifier.verify(da_blob))

    def test_verify_duplicated_blob(self):
        _ = TestEncoder()
        _.setUp()
        encoded_data = _.encoder.encode(_.data)
        columns = enumerate(encoded_data.extended_matrix.columns)
        i, column = next(columns)
        da_blob = DAShare(
            Column(column),
            i,
            encoded_data.combined_column_proofs[i],
            encoded_data.row_commitments,
        )
        self.assertIsNotNone(self.verifier.verify(da_blob))
        for i, column in columns:
            da_blob = DAShare(
                Column(column),
                i,
                encoded_data.combined_column_proofs[i],
                encoded_data.row_commitments,
            )
            self.assertIsNotNone(self.verifier.verify(da_blob))
