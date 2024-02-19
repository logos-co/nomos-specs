from da.common import NodeId
from da.verifier import DAVerifier

from da.mock.common import DaApiMessage
from da.mock.transport import Transport

class MockProducerNode:
    def __init__(self, node_id: NodeId):
        da_nodes: List[NodeId]
        self.verifier = DAVerifier()
        self.transport = Transport(node_id, self.handle_incoming_message)

    def connect(self, other_node):
        self.transport.connect(other_node.transport)

    def handle_incoming_message(self, transport, message: DaApiMessage):
        print("Producer got: ", message)
        match message:
            case CertificateMessage(certificate, meta):
                # Verify the certificate and put it in a block
                # In mock implementation - inform da nodes about new block
                pass

            case _:
                # Ignore other messages
                pass

