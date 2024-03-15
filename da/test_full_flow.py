from unittest import TestCase
from typing import List, Optional
from py_ecc.bls import G2ProofOfPossession as bls_pop

from da.common import Certificate, NodeId, build_attestation_message
from da.api.common import DAApi, VID, Metadata
from da.verifier import DAVerifier, DABlob 
from da.api.test_flow import MockStore
from da.dispersal import Dispersal, EncodedData, DispersalSettings
from da.test_encoder import TestEncoder
from da.encoder import DAEncoderParams, DAEncoder

class DAVerifierWApi():
    def __init__(self, sk: int):
        self.store = MockStore()
        self.api = DAApi(self.store)
        self.verifier = DAVerifier(sk)

    def receive_blob(self, blob: DABlob):
        if attestation := self.verifier.verify(blob):
            # Warning: If aggregated col commitment and row commitment are the same,
            # the build_attestation_message method will produce the same output.
            cert_id = build_attestation_message(blob.aggregated_column_commitment, blob.rows_commitments)
            self.store.populate(blob, cert_id)
            return attestation

    def receive_cert(self, vid: VID):
        # Usually the certificate would be verifier here, but we are assuming that this it is already comming from the verified block, in which case all certificates had been already verified by the DA Node.
        self.api.write(vid.cert_id, vid.metadata) 

    def read(self, app_id, indexes) -> List[Optional[DABlob]]:
        self.api.read(app_id, indexes)

class TestFullFlow(TestCase):
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

        self.api_nodes = [ DAVerifierWApi(k) for k in self.secret_keys ]


    def test_full_flow(self):
        app_id = int.to_bytes(1)
        index = 1

        # encoder
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_field_element=32)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        def __send_and_await_response(node: int, blob: DABlob):
            node = self.api_nodes[int.from_bytes(node)]
            return node.receive_blob(blob)

        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response
        certificate = self.dispersal.disperse(encoded_data)

        print(">>>>", self.api_nodes[0].store.blob_store)

        vid = VID(
                certificate.id(),
                Metadata(app_id, index)
            )

        # verifier
        for node in self.api_nodes:
            node.receive_cert(vid)

        # read from api and confirm its working
        blobs = [node.read(app_id, index) for node in self.api_nodes]
        blobs.sort(key = lambda x: x.index)
