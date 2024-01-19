import time
from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixNode
from mixnet.utils import random_bytes

CURRENT_ENTROPY = b"current entropy"


class MixnetTestCase(TestCase):
    @staticmethod
    def init(
        n_mix_nodes: int,
        n_layers: int,
        n_nodes_per_layer: int,
        entropy_delay_sec: int,
    ) -> Mixnet:
        assert n_layers * n_nodes_per_layer <= n_mix_nodes
        mix_nodes = [
            MixNode(
                generate_bls(),
                X25519PrivateKey.generate(),
                random_bytes(32),
            )
            for _ in range(n_mix_nodes)
        ]
        return Mixnet(
            mix_nodes,
            n_layers,
            n_nodes_per_layer,
            CURRENT_ENTROPY,
            entropy_delay_sec,
        )


class TestMixnet(MixnetTestCase):
    def test_topology(self):
        num_layers = 3
        num_nodes_per_layer = 3
        entropy_delay_sec = 5
        mixnet = self.init(12, num_layers, num_nodes_per_layer, entropy_delay_sec)

        # Check if topology was built with the expected size
        topology = mixnet.current_topology()
        self.assertEqual(len(topology.layers), num_layers)
        for layer in topology.layers:
            self.assertEqual(len(layer), num_nodes_per_layer)

        # Inject a new entropy
        mixnet.inject_entropy(b"new entropy")

        # But, check the current topology before the topology is updated after entropy_delay_sec
        self.assertEqual(mixnet.current_topology(), topology)

        # After some sleep, check if the topology has been updated
        time.sleep(entropy_delay_sec + 1)
        self.assertNotEqual(mixnet.current_topology(), topology)
