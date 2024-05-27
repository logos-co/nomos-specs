from unittest import TestCase

from da.common import Column, NomosDaG2ProofOfPossession as bls_pop
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY
from da.test_encoder import TestEncoder
from da.verifier import Attestation, DAVerifier, DABlob


class TestVerifier(TestCase):

    def setUp(self):
        self.verifier = DAVerifier(1987, [bls_pop.SkToPk(1987)])

    def test_verify_column(self):
        column = Column(int.to_bytes(i, length=32) for i in range(8))
        _, column_commitment = kzg.bytes_to_commitment(column.as_bytes(), GLOBAL_PARAMETERS)
        aggregated_poly, aggregated_column_commitment = kzg.bytes_to_commitment(
            DAEncoder.hash_column_and_commitment(column, column_commitment), GLOBAL_PARAMETERS
        )
        aggregated_proof = kzg.generate_element_proof(0, aggregated_poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
        self.assertTrue(
            self.verifier._verify_column(
                column, column_commitment, aggregated_column_commitment, aggregated_proof, 0
            )
        )

    def test_verify(self):
        _ = TestEncoder()
        _.setUp()
        encoded_data = _.encoder.encode(_.data)
        verifiers_sk = [i for i in range(1000, 1000+len(encoded_data.chunked_data[0]))]
        vefiers_pk = [bls_pop.SkToPk(k) for k in verifiers_sk]
        for i, column in enumerate(encoded_data.chunked_data.columns):
            verifier = DAVerifier(verifiers_sk[i], vefiers_pk)
            da_blob = DABlob(
                Column(column),
                encoded_data.column_commitments[i],
                encoded_data.aggregated_column_commitment,
                encoded_data.aggregated_column_proofs[i],
                encoded_data.row_commitments,
                [row[i] for row in encoded_data.row_proofs],
            )
            self.assertIsNotNone(verifier.verify(da_blob))

    def test_verify_duplicated_blob(self):
        _ = TestEncoder()
        _.setUp()
        encoded_data = _.encoder.encode(_.data)
        columns = enumerate(encoded_data.chunked_data.columns)
        i, column = next(columns)
        da_blob = DABlob(
            Column(column),
            encoded_data.column_commitments[i],
            encoded_data.aggregated_column_commitment,
            encoded_data.aggregated_column_proofs[i],
            encoded_data.row_commitments,
            [row[i] for row in encoded_data.row_proofs],
        )
        self.assertIsNotNone(self.verifier.verify(da_blob))
        for i, column in columns:
            da_blob = DABlob(
                Column(column),
                encoded_data.column_commitments[i],
                encoded_data.aggregated_column_commitment,
                encoded_data.aggregated_column_proofs[i],
                encoded_data.row_commitments,
                [row[i] for row in encoded_data.row_proofs],
            )
            self.assertIsNone(self.verifier.verify(da_blob))
