from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixnetTopologySize, MixNode
from mixnet.robustness import Robustness
from mixnet.utils import random_bytes


class TestRobustness(TestCase):
    def test_build_topology(self):
        robustness = Robustness(
            [
                MixNode(
                    generate_bls(),
                    X25519PrivateKey.generate(),
                    random_bytes(32),
                )
                for _ in range(12)
            ],
            MixnetTopologySize(3, 3),
            Mixnet(),
        )

        topology = robustness.build_topology(b"entropy")
        self.assertEqual(
            len(topology.layers), robustness.mixnet_topology_size.num_layers
        )
        for layer in topology.layers:
            self.assertEqual(
                len(layer), robustness.mixnet_topology_size.num_mixnodes_per_layer
            )
