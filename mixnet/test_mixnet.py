from unittest import IsolatedAsyncioTestCase

from mixnet.mixnet import Mixnet
from mixnet.robustness import Robustness, RobustnessConfig
from mixnet.test_utils import init_robustness_mixnet_config


class TestMixnet(IsolatedAsyncioTestCase):
    async def test_topology_from_robustness(self):
        robustness_mixnet_config = init_robustness_mixnet_config()

        mixnet = await Mixnet.new(
            robustness_mixnet_config.mixnode_candidates[0].encryption_private_key,
            robustness_mixnet_config.mixnet_layer_config,
        )
        try:
            robustness = Robustness(RobustnessConfig(robustness_mixnet_config), mixnet)
            self.assertEqual(
                robustness_mixnet_config.mixnet_layer_config, mixnet.get_config()
            )

            old_topology = robustness_mixnet_config.mixnet_layer_config.topology
            robustness.set_entropy(b"new entropy")
            self.assertNotEqual(old_topology, mixnet.get_config().topology)
        finally:
            await mixnet.cancel()
