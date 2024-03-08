from unittest import TestCase

from da.common import Column
from da.encoder import DAEncoder
from da.kzg_rs import kzg
from da.kzg_rs.common import GLOBAL_PARAMETERS, ROOTS_OF_UNITY
from da.test_encoder import TestEncoder
from da.verifier import Attestation, DAVerifier, DABlob


class TestVerifier(TestCase):

    def setUp(self):
        self.verifier = DAVerifier()

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
    def test_verify_chunk(self):
        pass

    def test_build_attestation(self):
        pass

    def test_verify(self):
        pass
