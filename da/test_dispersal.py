from hashlib import sha3_256
from unittest import TestCase

from .encoder import DAEncoderParams, DAEncoder
from .test_encoder import TestEncoder

from da.common import NodeId, Attestation, Bitfield
from da.dispersal import Dispersal, EncodedData, DispersalSettings
from py_ecc.bls import G2ProofOfPossession as bls_pop

from .verifier import DAVerifier, DABlob


class TestDispersal(TestCase):
    def setUp(self):
        self.n_nodes = 16
        self.nodes_ids = [NodeId(x.to_bytes(length=32, byteorder='big')) for x in range(self.n_nodes)]
        self.secret_keys = list(range(1, self.n_nodes+1))
        self.public_keys = [bls_pop.SkToPk(sk) for sk in self.secret_keys]
        dispersal_settings = DispersalSettings(
            self.nodes_ids,
            self.public_keys,
            self.n_nodes // 2 + 1
        )
        self.dispersal = Dispersal(dispersal_settings)
        self.encoder_test = TestEncoder()
        self.encoder_test.setUp()

    def test_build_certificate_insufficient_attestations(self):
        with self.assertRaises(AssertionError):
            self.dispersal._build_certificate(None, [], [])

    def test_build_certificate_enough_attestations(self):
        mock_encoded_data = EncodedData(
            None, None, None, [], [], [], bytes(b"f"*48), []
        )
        mock_message = sha3_256(mock_encoded_data.aggregated_column_commitment).digest()
        mock_attestations = [Attestation(bls_pop.Sign(sk, mock_message)) for sk in self.secret_keys]
        certificate = self.dispersal._build_certificate(
            mock_encoded_data,
            mock_attestations,
            Bitfield([True for _ in range(len(self.secret_keys))])
        )
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.aggregated_column_commitment, mock_encoded_data.aggregated_column_commitment)
        self.assertEqual(certificate.row_commitments, [])
        self.assertIsNotNone(certificate.aggregated_signatures)
        self.assertTrue(
            bls_pop.AggregateVerify(self.public_keys, [mock_message]*len(self.public_keys), certificate.aggregated_signatures)
        )

    def test_disperse(self):
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_field_element=32)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        def __send_and_await_response(node: NodeId, blob: DABlob):
            sk = self.secret_keys[int.from_bytes(node)]
            verifier = DAVerifier(sk)
            return verifier.verify(blob)
        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response

        certificate = self.dispersal.disperse(encoded_data)
        self.assertIsNotNone(certificate)
        self.assertTrue(
            bls_pop.AggregateVerify(
                self.public_keys[:self.dispersal.settings.threshold],
                [self.dispersal._build_attestation_message(encoded_data)]*self.dispersal.settings.threshold,
                certificate.aggregated_signatures
            )
        )
        self.assertEqual(
            certificate.signers,
            [True if i < self.dispersal.settings.threshold else False for i in range(self.n_nodes)]
        )

