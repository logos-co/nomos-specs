import unittest
from unittest.mock import Mock, patch
from typing import List

from da.common import NodeId
from da.encoder import DAEncoderParams
from eth2spec.eip7594.mainnet import BYTES_PER_FIELD_ELEMENT

from da.mock.zone import MockZoneNode, MockZoneParams

class TestDaReadWrite(unittest.TestCase):
    def test_happy_write(self):
        da_node_ids = []
        da_node_ids.append(NodeId("11"*32))
        da_node_ids.append(NodeId("22"*32))
        da_node_ids.append(NodeId("33"*32))

        block_producer_id = NodeId("00"*32)
        zone_node_id = NodeId("99"*32)

        encoder_params = DAEncoderParams(
            column_count=10,
            bytes_per_field_element=BYTES_PER_FIELD_ELEMENT
        )

        zone = MockZoneNode(zone_node_id, MockZoneParams(
            da_node_ids, 
            block_producer_id,
            len(da_node_ids),
            encoder_params,
        ))

