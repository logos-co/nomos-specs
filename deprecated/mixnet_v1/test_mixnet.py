import asyncio
from unittest import IsolatedAsyncioTestCase

from deprecated.mixnet_v1.mixnet import Mixnet
from deprecated.mixnet_v1.test_utils import init_mixnet_config


class TestMixnet(IsolatedAsyncioTestCase):
    async def test_topology_from_robustness(self):
        config = init_mixnet_config()
        entropy_queue = asyncio.Queue()

        mixnet = await Mixnet.new(config, entropy_queue)
        try:
            old_topology = config.mixclient_config.topology
            await entropy_queue.put(b"new entropy")
            await asyncio.sleep(1)
            self.assertNotEqual(old_topology, mixnet.get_topology())
        finally:
            await mixnet.cancel()
