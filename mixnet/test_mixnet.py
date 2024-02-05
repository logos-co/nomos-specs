from typing import Tuple
from unittest import IsolatedAsyncioTestCase

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixnetTopologySize, MixNode
from mixnet.robustness import Robustness
from mixnet.utils import random_bytes


class TestMixnet(IsolatedAsyncioTestCase):
    @staticmethod
    def init() -> Tuple[Mixnet, Robustness]:
        mixnet = Mixnet()
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
            mixnet,
        )
        robustness.set_entropy(b"entropy")

        return (mixnet, robustness)

    def test_topology_from_robustness(self):
        mixnet, robustness = self.init()

        topology1 = mixnet.get_topology()

        robustness.set_entropy(b"new entropy")
        topology2 = mixnet.get_topology()

        self.assertNotEqual(topology1, topology2)
