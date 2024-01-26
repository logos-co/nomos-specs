from typing import List
from unittest import TestCase

from pysphinx.sphinx import ProcessedFinalHopPacket, SphinxPacket

from mixnet.packet import (
    Fragment,
    MessageFlag,
    MessageReconstructor,
    PacketBuilder,
)
from mixnet.test_utils import initial_topology
from mixnet.topology import MixNodeInfo
from mixnet.utils import random_bytes


class TestPacket(TestCase):
    def test_real_packet(self):
        topology = initial_topology()
        msg = random_bytes(3500)
        builder = PacketBuilder.real(msg, topology)
        packet0, route0 = builder.next()
        packet1, route1 = builder.next()
        packet2, route2 = builder.next()
        packet3, route3 = builder.next()
        self.assertRaises(StopIteration, builder.next)

        reconstructor = MessageReconstructor()
        self.assertIsNone(
            reconstructor.add(self.process_packet(packet1, route1)),
        )
        self.assertIsNone(
            reconstructor.add(self.process_packet(packet3, route3)),
        )
        self.assertIsNone(
            reconstructor.add(self.process_packet(packet2, route2)),
        )
        msg_with_flag = reconstructor.add(self.process_packet(packet0, route0))
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag),
            (MessageFlag.MESSAGE_FLAG_REAL, msg),
        )

    def test_cover_packet(self):
        topology = initial_topology()
        msg = b"cover"
        builder = PacketBuilder.drop_cover(msg, topology)
        packet, route = builder.next()
        self.assertRaises(StopIteration, builder.next)

        reconstructor = MessageReconstructor()
        msg_with_flag = reconstructor.add(self.process_packet(packet, route))
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag),
            (MessageFlag.MESSAGE_FLAG_DROP_COVER, msg),
        )

    @staticmethod
    def process_packet(packet: SphinxPacket, route: List[MixNodeInfo]) -> Fragment:
        processed = packet.process(route[0].encryption_private_key)
        if isinstance(processed, ProcessedFinalHopPacket):
            return Fragment.from_bytes(processed.payload.recover_plain_playload())
        else:
            processed = processed
            for node in route[1:]:
                p = processed.next_packet.process(node.encryption_private_key)
                if isinstance(p, ProcessedFinalHopPacket):
                    return Fragment.from_bytes(p.payload.recover_plain_playload())
                else:
                    processed = p
            assert False
