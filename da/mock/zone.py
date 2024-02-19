from dataclasses import dataclass
from typing import List, Optional, Generator

from da.common import Certificate, NodeId, Attestation
from da.dispersal import Dispersal
from da.encoder import EncodedData, DAEncoder, DAEncoderParams
from da.verifier import Attestation, DABlob, DAVerifier

from da.mock.common import CertificateMessage, DaApiMessage, Id, Metadata, data_hash
from da.mock.node import MockDaNode
from da.mock.producer import MockProducerNode
from da.mock.transport import Transport

@dataclass
class MockZoneParams:
    da_nodes: List[MockDaNode]
    block_producer: MockProducerNode
    threshold: int
    encoder_params: DAEncoderParams

class MockZoneNode:
    def __init__(self, node_id: NodeId, params: MockZoneParams):
        self.data_attestations = {}
        self.params = params
        self.dispersal = Dispersal(nodes=params.da_nodes, threshold=params.threshold)
        self.encoder = DAEncoder(params.encoder_params)
        self.transport = Transport(node_id, self.handle_incoming_message)

    def _create_blobs(self, data: bytearray) -> Generator[DABlob, None, None]:
        # Encodes data and returns DABlob for disemination.
        encoded_data = self.encoder.encode(data)
        return self.dispersal._prepare_data(encoded_data)

    def _create_certificate(self, attestations: List[Attestation]) -> Optional[Certificate]:
        # Creates a certificate from the list of Attestations.
        return self.dispersal._build_certificate(attestations)

    def connect(self, other_node):
        self.transport.connect(other_node.transport)

    def disperse_data(self, data: bytearray, meta: Metadata):
        self.data_attestations[data_hash(data)] = []
        blobs = self._create_blobs(data)

        for node, blob in zip(self.params.da_nodes, blobs):
            message = DABlobMessage(blob, meta)
            self.transport.send_message(node, message)

    def disperse_certificate(self, certificate: Certificate, meta: Metadata):
        message = CertificateMessage(certificate, meta)

        for producer in self.params.block_producers:
            self.transport.send_message(producer, message)

    def handle_incoming_message(self, transport, message: DaApiMessage):
        print("Zone got: ", message)
        # Receive DA Api message and act on it.
        match message:
            case AttestationMessage(blob_id, attestation, meta):
                da_node = message.sender

                # Collect attestations for a certain data blob and form a certificate
                # once a threshold is reached.
                if blob_id not in self.blob_attestations:
                    self.blob_attestations[blob_id] = []
                    self.blob_attestations[blob_id].append(attestation)

                if len(self.blob_attestations[blob_id]) >= self.params.threshold:
                    certificate = self._create_certificate(self.blob_attestations[blob_id])
                    self.disperse_certificate(certificate, meta)

                # Respond to sender (mock implementation detail)
                self.transport.send_message(da_node, None)

            case _:
                # Ignore other messages
                pass 

