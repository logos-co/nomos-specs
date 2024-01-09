from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixNode
from mixnet.utils import random_bytes


class TestMixnet(TestCase):
    def test_build_topology(self):
        nodes = [
            MixNode.build(generate_bls(), X25519PrivateKey.generate(), random_bytes(32))
            for i in range(12)
        ]
        mixnet = Mixnet(nodes)

        topology = mixnet.build_topology(b"entropy", 3, 3)
        self.assertEqual(len(topology.layers), 3)
        for layer in topology.layers:
            self.assertEqual(len(layer), 3)
