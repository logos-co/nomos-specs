from unittest import TestCase

from bls import generate_bls
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from utils import random_bytes

from mixnet import Mixnet, MixNode


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
