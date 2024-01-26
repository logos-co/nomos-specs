from unittest import IsolatedAsyncioTestCase

from mixnet.mixnet import Mixnet
from mixnet.robustness import Robustness
from mixnet.test_utils import init


class TestMixnet(IsolatedAsyncioTestCase):
    async def test_topology_from_robustness(self):
        mixnode_candidates, topology_size = init()
        initial_topology = Robustness.build_topology(
            mixnode_candidates, topology_size, b"entropy"
        )

        mixnet = await Mixnet.new(
            initial_topology, 30, 3, mixnode_candidates[0].encryption_private_key, 30
        )
        try:
            robustness = Robustness(mixnode_candidates, topology_size, mixnet)
            self.assertEqual(initial_topology, mixnet.get_topology())

            robustness.set_entropy(b"new entropy")
            self.assertNotEqual(initial_topology, mixnet.get_topology())
        finally:
            await mixnet.cancel()
