from dataclasses import dataclass
from typing import List, Optional, Generator

from da.common import NodeId
from da.verifier import DAVerifier

from da.mock.common import DaApiMessage
from da.mock.transport import Transport

class MockDaNode:
    def __init__(self, node_id: NodeId):
        self.app_blobs_cache = {}
        self.verifier = DAVerifier()
        self.transport = Transport(node_id, self.handle_incoming_message)

    def handle_incoming_message(self, transport, message: DaApiMessage):
        print("DA Node got: ", message)
        # Receive DA Api message and act on it.
        match message:
            case DABlobMessage(blob, meta):
                zone_id = message.sender

                # Verify the blob and create attestation.
                attestation = self.verifier.verify(blob)
                if attestation != None:
                    # Append blob data to application data cache.
                    self.app_blobs_cache[meta] = blob

                # Responde either way (mock implementation detail)
                response = AttestationMessage(attestation, meta)
                self.transport.send_message(zone_id, response)

            case BlockMessage(block_id, vids):
                # Make cached app blobs abailable if they are in block
                pass

            case _:
                # Ignore other messages
                pass 
