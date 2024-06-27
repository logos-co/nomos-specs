from hashlib import sha3_256
from unittest import TestCase

from da.encoder import DAEncoderParams, DAEncoder
from da.test_encoder import TestEncoder
from da.verifier import DAVerifier, DABlob
from da.common import NodeId, Attestation, Bitfield, NomosDaG2ProofOfPossession as bls_pop
from da.dispersal import Dispersal, EncodedData, DispersalSettings


class TestDispersal(TestCase):
    def setUp(self):
        self.n_nodes = 16
        self.nodes_ids = [NodeId(x.to_bytes(length=32, byteorder='big')) for x in range(self.n_nodes)]
        self.secret_keys = list(range(1, self.n_nodes+1))
        self.public_keys = [bls_pop.SkToPk(sk) for sk in self.secret_keys]
        # sort by pk as we do in dispersal
        self.secret_keys, self.public_keys = zip(
            *sorted(zip(self.secret_keys, self.public_keys), key=lambda x: x[1])
        )
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
            certificate.verify(self.public_keys)
        )

    def test_disperse(self):
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_chunk=31)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        def __send_and_await_response(node: NodeId, blob: DABlob):
            sk = self.secret_keys[int.from_bytes(node)]
            verifier = DAVerifier(sk, self.public_keys)
            return verifier.verify(blob)
        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response

        certificate = self.dispersal.disperse(encoded_data)
        self.assertIsNotNone(certificate)
        self.assertTrue(certificate.verify(self.public_keys)
        )
        self.assertEqual(
            certificate.signers,
            [True if i < self.dispersal.settings.threshold else False for i in range(self.n_nodes)]
        )

