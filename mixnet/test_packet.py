from typing import List, Tuple
from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixnetTopology, MixNode
from mixnet.packet import (
    MESSAGE_FLAG_DROP_COVER,
    MESSAGE_FLAG_REAL,
    Fragment,
    MessageReconstructor,
    PacketBuilder,
)
from mixnet.sphinx.sphinx import ProcessedFinalHopPacket, SphinxPacket
from mixnet.utils import random_bytes


class TestPacket(TestCase):
    def test_real_packet(self):
        mixnet, topology = self.init()

        msg = random_bytes(3500)
        packets, routes = PacketBuilder.build_real_packets(msg, mixnet, topology)
        self.assertEqual(len(packets), 4)
        self.assertEqual(len(packets), len(routes))

        reconstructor = MessageReconstructor.new()
        self.assertIsNone(
            reconstructor.add(self.process_packet(packets[1], routes[1])),
        )
        self.assertIsNone(
            reconstructor.add(self.process_packet(packets[3], routes[3])),
        )
        self.assertIsNone(
            reconstructor.add(self.process_packet(packets[2], routes[2])),
        )
        msg_with_flag = reconstructor.add(self.process_packet(packets[0], routes[0]))
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag), (MESSAGE_FLAG_REAL, msg)
        )

    def test_cover_packet(self):
        mixnet, topology = self.init()

        packet, route = PacketBuilder.build_drop_cover_packet(mixnet, topology)

        reconstructor = MessageReconstructor.new()
        msg_with_flag = reconstructor.add(self.process_packet(packet, route))
        assert msg_with_flag is not None
        self.assertEqual(
            PacketBuilder.parse_msg_and_flag(msg_with_flag),
            (MESSAGE_FLAG_DROP_COVER, b""),
        )

    @staticmethod
    def init() -> Tuple[Mixnet, MixnetTopology]:
        mixnet = Mixnet(
            [
                MixNode(
                    generate_bls(),
                    X25519PrivateKey.generate(),
                    random_bytes(32),
                )
                for _ in range(12)
            ]
        )
        topology = mixnet.build_topology(b"entropy", 3, 3)
        return mixnet, topology

    @staticmethod
    def process_packet(packet: SphinxPacket, route: List[MixNode]) -> Fragment:
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
