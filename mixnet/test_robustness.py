from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.robustness import Robustness
from mixnet.topology import MixnetTopologySize, MixNodeInfo
from mixnet.utils import random_bytes


class TestRobustness(TestCase):
    def test_build_topology(self):
        mixnode_candidates = [
            MixNodeInfo(
                generate_bls(),
                X25519PrivateKey.generate(),
                random_bytes(32),
            )
            for _ in range(12)
        ]
        topology_size = MixnetTopologySize(3, 3)

        topology = Robustness.build_topology(
            mixnode_candidates, topology_size, b"entropy"
        )
        self.assertEqual(len(topology.layers), topology_size.num_layers)
        for layer in topology.layers:
            self.assertEqual(len(layer), topology_size.num_mixnodes_per_layer)
