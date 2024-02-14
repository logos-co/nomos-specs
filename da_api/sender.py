from typing import List, Optional, Generator

from da_api.common import DABlobWMetadata, CertificateWMetadata
from da.common import Certificate, NodeId
from da.dispersal import Dispersal
from da.encoder import EncodedData

class Sender:
    def __init__(self, da_nodes: List[NodeId], block_producers: List[NodeId], threshold: int):
        self.da_nodes = da_nodes
        self.block_producers = block_producers
        self.threshold = int
        self.dispersal = Dispersal(nodes=da_nodes, threshold=threshold)

    def disperse(self, encoded_data: EncodedData) -> Optional[Certificate]:
        # Sends DABlob to receivers (DA Nodes).
        return self.dispersal._disperse(encoded_data)

    def send_and_await_producer(self, producer: NodeId, certificate: Certificate):
        # Sends Certificate to the block producer.
        # TODO: write to producer outbound queue.
        pass
