from itertools import chain
from unittest import TestCase
from typing import List, Optional

from da.common import NodeId, build_blob_id, NomosDaG2ProofOfPossession as bls_pop
from da.api.common import DAApi, BlobMetadata, Metadata
from da.verifier import DAVerifier, DABlob 
from da.api.test_flow import MockStore
from da.dispersal import Dispersal, DispersalSettings
from da.test_encoder import TestEncoder
from da.encoder import DAEncoderParams, DAEncoder


class DAVerifierWApi:
    def __init__(self):
        self.store = MockStore()
        self.api = DAApi(self.store)
        self.verifier = DAVerifier()

    def receive_blob(self, blob: DABlob):
        if self.verifier.verify(blob):
            # Warning: If aggregated col commitment and row commitment are the same,
            # the build_attestation_message method will produce the same output.
            blob_id = build_blob_id(blob.aggregated_column_commitment, blob.rows_commitments)
            self.store.populate(blob, blob_id)

    def receive_metadata(self, blob_metadata: BlobMetadata):
        # Usually the certificate would be verifier here,
        # but we are assuming that this it is already coming from the verified block,
        # in which case all certificates had been already verified by the DA Node.
        self.api.write(blob_metadata.blob_id, blob_metadata.metadata)

    def read(self, app_id, indexes) -> List[Optional[DABlob]]:
        return self.api.read(app_id, indexes)


class TestFullFlow(TestCase):
    def setUp(self):
        self.n_nodes = 16
        self.nodes_ids = [NodeId(x.to_bytes(length=32, byteorder='big')) for x in range(self.n_nodes)]
        # sort by pk as we do in dispersal
        dispersal_settings = DispersalSettings(
            self.nodes_ids,
            self.n_nodes
        )
        self.dispersal = Dispersal(dispersal_settings)
        self.encoder_test = TestEncoder()
        self.encoder_test.setUp()

        self.api_nodes = [DAVerifierWApi() for _ in range(self.n_nodes)]

    def test_full_flow(self):
        app_id = int.to_bytes(1)
        index = 1

        # encoder
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_chunk=31)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        def __send_and_await_response(node: int, blob: DABlob):
            node = self.api_nodes[int.from_bytes(node)]
            node.receive_blob(blob)

        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response
        blob_id = build_blob_id(encoded_data.aggregated_column_commitment, encoded_data.row_commitments)
        blob_metadata = BlobMetadata(
            blob_id,
            Metadata(app_id, index)
        )

        # verifier
        for node in self.api_nodes:
            node.receive_metadata(blob_metadata)

        # read from api and confirm its working
        # notice that we need to sort the api_nodes by their public key to have the blobs sorted in the same fashion
        # we do actually do dispersal.
        blobs = list(chain.from_iterable(
            node.read(app_id, [index])
            for node in self.api_nodes
        ))
        original_blobs = list(self.dispersal._prepare_data(encoded_data))
        self.assertEqual(blobs, original_blobs)

    def test_same_blob_multiple_indexes(self):
        app_id = int.to_bytes(1)
        indexes = [1, 2, 3]  # Different indexes to test with the same blob

        # encoder
        data = self.encoder_test.data
        encoding_params = DAEncoderParams(column_count=self.n_nodes // 2, bytes_per_chunk=31)
        encoded_data = DAEncoder(encoding_params).encode(data)

        # mock send and await method with local verifiers
        def __send_and_await_response(node: int, blob: DABlob):
            node = self.api_nodes[int.from_bytes(node)]
            return node.receive_blob(blob)

        # inject mock send and await method
        self.dispersal._send_and_await_response = __send_and_await_response
        self.dispersal.disperse(encoded_data)
        blob_id = build_blob_id(encoded_data.aggregated_column_commitment, encoded_data.row_commitments)

        # Loop through each index and simulate dispersal with the same cert_id but different metadata
        for index in indexes:
            metadata = BlobMetadata(
                blob_id,
                Metadata(app_id, index)
            )

            # verifier
            for node in self.api_nodes:
                node.receive_metadata(metadata)

        # Verify retrieval for each index
        for index in indexes:
            # Notice that we need to sort the api_nodes by their public key to have the blobs sorted in the same fashion
            # as we do actually do dispersal.
            blobs = list(chain.from_iterable(
                node.read(app_id, [index])
                for node in self.api_nodes
            ))
            original_blobs = list(self.dispersal._prepare_data(encoded_data))
            self.assertEqual(blobs, original_blobs, f"Failed at index {index}")
