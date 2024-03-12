from hashlib import sha3_256
from unittest import TestCase

from da.common import NodeId, Attestation
from da.dispersal import Dispersal, DABlob, EncodedData, DispersalSettings
from py_ecc.bls import G2ProofOfPossession as bls_pop


class TestDispersal(TestCase):
    def setUp(self):
        self.nodes_ids = [NodeId(x.to_bytes(length=32, byteorder='big')) for x in range(10)]
        self.secret_keys = list(range(1, 11))
        self.public_keys = [bls_pop.SkToPk(sk) for sk in self.secret_keys]
        dispersal_settings = DispersalSettings(
            self.nodes_ids,
            self.public_keys,
            6
        )
        self.dispersal = Dispersal(dispersal_settings)

    def test_build_certificate_insufficient_attestations(self):
        with self.assertRaises(AssertionError):
            self.dispersal._build_certificate(None, [])


    def test_build_certificate_enough_attestations(self):
        mock_encoded_data = EncodedData(
            None, None, None, [], [], [], bytes(b"f"*48), []
        )
        mock_message = sha3_256(mock_encoded_data.aggregated_column_commitment).digest()
        mock_attestations = [Attestation(bls_pop.Sign(sk, mock_message)) for sk in self.secret_keys]
        certificate = self.dispersal._build_certificate(mock_encoded_data, mock_attestations)
        self.assertIsNotNone(certificate)
        self.assertEqual(certificate.aggregated_column_commitment, mock_encoded_data.aggregated_column_commitment)
        self.assertEqual(certificate.row_commitments, [])
        self.assertIsNotNone(certificate.aggregated_signatures)
        self.assertTrue(
            bls_pop.AggregateVerify(self.public_keys, [mock_message]*len(self.public_keys), certificate.aggregated_signatures)
        )

    def test_prepare_data(self):
        pass

    def test_verify_attestation(self):
        pass

    def test_disperse(self):
        pass
