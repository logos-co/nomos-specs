import da.mock.common import DaApiMessage

class MockProducerNode:
    def __init__(self, node_id: NodeId):
        da_nodes: List[NodeId]
        self.verifier = DAVerifier()
        self.transport = Transport(node_id, self.handle_incoming_message)

    def handle_incoming_message(self, transport, message: DaApiMessage):
        match message:
            case CertificateMessage(certificate, meta):
                # Verify the certificate and put it in a block
                # In mock implementation - inform da nodes about new block
                pass

            case _:
                # Ignore other messages
                pass

