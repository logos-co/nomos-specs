import time
from unittest import TestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixNode
from mixnet.utils import random_bytes

INITIAL_ENTROPY = b"initial entropy"


class MixnetTestCase(TestCase):
    @staticmethod
    def init(
        n_mix_nodes: int,
        n_layers: int,
        n_nodes_per_layer: int,
        mixnet_epoch_sec: int,
        proactive_sec: int,
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
            mixnet_epoch_sec,
            proactive_sec,
            INITIAL_ENTROPY,
        )


class TestMixnet(MixnetTestCase):
    def test_topology(self):
        mixnet = self.init(12, 3, 3, 3, 1)

        # Check if topology was built with the expected size
        topology = mixnet.current_topology()
        self.assertEqual(len(topology.layers), 3)
        for layer in topology.layers:
            self.assertEqual(len(layer), 3)

        # Check if topology is updated periodically
        time.sleep(4)
        new_topology = mixnet.current_topology()
        self.assertNotEqual(new_topology, topology)

        # Check if the topology same as the initial topology is generated
        # if the entropy is reset with the initial entropy
        mixnet.set_entropy(INITIAL_ENTROPY)
        time.sleep(4)
        new_topology = mixnet.current_topology()
        self.assertEqual(new_topology, topology)
