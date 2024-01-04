from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixNode
from mixnet.utils import random_bytes
from mixnet.sphinx.sphinx import (
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
)


class TestSphinx(TestCase):
    def test_sphinx(self):
        mixnet = Mixnet(
            [
                MixNode(generate_bls(), X25519PrivateKey.generate(), random_bytes(32))
                for _ in range(12)
            ]
        )
        topology = mixnet.build_topology(b"entropy", 3, 3)

        msg = random_bytes(500)
        route = topology.generate_route()
        destination = mixnet.choose_mixnode()

        packet = SphinxPacket.build(msg, route, destination)

        # Process packet with the first mix node in the route
        processed_packet = packet.process(route[0].encryption_private_key)
        if not isinstance(processed_packet, ProcessedForwardHopPacket):
            self.fail()
        self.assertEqual(processed_packet.next_node_address, route[1].addr)

        # Process packet with the second mix node in the route
        processed_packet = processed_packet.next_packet.process(
            route[1].encryption_private_key
        )
        if not isinstance(processed_packet, ProcessedForwardHopPacket):
            self.fail()
        self.assertEqual(processed_packet.next_node_address, route[2].addr)

        # Process packet with the third mix node in the route
        processed_packet = processed_packet.next_packet.process(
            route[2].encryption_private_key
        )
        if not isinstance(processed_packet, ProcessedFinalHopPacket):
            self.fail()
        self.assertEqual(processed_packet.destination_node_address, destination.addr)

        # Verify message as a destination
        self.assertEqual(processed_packet.payload.recover_plain_playload(), msg)
