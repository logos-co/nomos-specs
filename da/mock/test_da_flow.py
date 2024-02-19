import unittest
from unittest.mock import Mock, patch
from typing import List

from da.common import NodeId 
from da.encoder import DAEncoderParams
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT

from da.mock.common import Metadata
from da.mock.node import MockDaNode
from da.mock.producer import MockProducerNode
from da.mock.zone import MockZoneNode, MockZoneParams

class TestDaReadWrite(unittest.TestCase):
    def test_happy_write(self):
        encoder_params = DAEncoderParams(
            column_count=10,
            bytes_per_field_element=BYTES_PER_FIELD_ELEMENT
        )

        da_nodes = []
        da_nodes.append(MockDaNode(NodeId("11"*32)))
        da_nodes.append(MockDaNode(NodeId("22"*32)))
        da_nodes.append(MockDaNode(NodeId("33"*32)))

        block_producer = MockProducerNode("00"*32)

        zone = MockZoneNode(NodeId("99"*32), MockZoneParams(
            da_nodes, 
            block_producer,
            len(da_nodes),
            encoder_params,
        ))

        for da_node in da_nodes:
            zone.connect(da_node)
            block_producer.connect(da_node)

        zone.connect(block_producer)
        
        meta = Metadata(1, "App1")
        zone.disperse_data("hello", meta)
