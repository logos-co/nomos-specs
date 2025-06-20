from unittest import TestCase

from da.encoder import DAEncoderParams, DAEncoder
from da.test_encoder import TestEncoder
from da.verifier import DAVerifier, DAShare
from da.common import NodeId
from da.dispersal import Dispersal, DispersalSettings


class TestDispersal(TestCase):
    def setUp(self):
        self.n_nodes = 16
        self.nodes_ids = [NodeId(x.to_bytes(length=32, byteorder='big')) for x in range(self.n_nodes)]
        dispersal_settings = DispersalSettings(
            self.nodes_ids,
            self.n_nodes // 2 + 1
        )
        self.dispersal = Dispersal(dispersal_settings)
        self.encoder_test = TestEncoder()
        self.encoder_test.setUp()

    def test_disperse(self):
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_chunk=31)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        verifiers_res = []
        def __send_and_await_response(_, blob: DAShare):
            verifier = DAVerifier()
            res = verifier.verify(blob)
            verifiers_res.append(res)
            return res
        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response
        self.dispersal.disperse(encoded_data)
        for res in verifiers_res:
            self.assertTrue(res)

