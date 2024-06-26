from random import randint
from typing import List
from unittest import TestCase

from pysphinx.sphinx import ProcessedFinalHopPacket, SphinxPacket

from mixnet.config import NodeInfo
from mixnet.packet import (
    Fragment,
    MessageFlag,
    MessageReconstructor,
    PacketBuilder,
)
from mixnet.test_utils import init_mixnet_config


class TestPacket(TestCase):
    def test_real_packet(self):
        membership = init_mixnet_config(10).membership
        msg = self.random_bytes(3500)
        packets_and_routes = PacketBuilder.build_real_packets(msg, membership)
        self.assertEqual(4, len(packets_and_routes))

        reconstructor = MessageReconstructor()
        self.assertIsNone(
            reconstructor.add(
                self.process_packet(packets_and_routes[1][0], packets_and_routes[1][1])
            ),
        )
        self.assertIsNone(
            reconstructor.add(
                self.process_packet(packets_and_routes[3][0], packets_and_routes[3][1])
            ),
        )
        self.assertIsNone(
            reconstructor.add(
                self.process_packet(packets_and_routes[2][0], packets_and_routes[2][1])
            ),
        )
        msg_with_flag = reconstructor.add(
            self.process_packet(packets_and_routes[0][0], packets_and_routes[0][1])
        )
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag),
            (MessageFlag.MESSAGE_FLAG_REAL, msg),
        )

    def test_cover_packet(self):
        membership = init_mixnet_config(10).membership
        msg = b"cover"
        packets_and_routes = PacketBuilder.build_drop_cover_packets(msg, membership)
        self.assertEqual(1, len(packets_and_routes))

        reconstructor = MessageReconstructor()
        msg_with_flag = reconstructor.add(
            self.process_packet(packets_and_routes[0][0], packets_and_routes[0][1])
        )
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag),
            (MessageFlag.MESSAGE_FLAG_DROP_COVER, msg),
        )

    @staticmethod
    def process_packet(packet: SphinxPacket, route: List[NodeInfo]) -> Fragment:
        processed = packet.process(route[0].private_key)
        if isinstance(processed, ProcessedFinalHopPacket):
            return Fragment.from_bytes(processed.payload.recover_plain_playload())
        else:
            processed = processed
            for node in route[1:]:
                p = processed.next_packet.process(node.private_key)
                if isinstance(p, ProcessedFinalHopPacket):
                    return Fragment.from_bytes(p.payload.recover_plain_playload())
                else:
                    processed = p
            assert False

    @staticmethod
    def random_bytes(size: int) -> bytes:
        assert size >= 0
        return bytes([randint(0, 255) for _ in range(size)])
