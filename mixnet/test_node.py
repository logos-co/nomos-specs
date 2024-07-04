import asyncio
from unittest import IsolatedAsyncioTestCase

import mixnet.framework.asyncio as asynciofw
from mixnet.connection import LocalSimplexConnection
from mixnet.node import Node
from mixnet.test_utils import (
    init_mixnet_config,
)


class TestNode(IsolatedAsyncioTestCase):
    async def test_node(self):
        framework = asynciofw.Framework()
        global_config, node_configs, _ = init_mixnet_config(10)
        nodes = [
            Node(framework, node_config, global_config) for node_config in node_configs
        ]
        for i, node in enumerate(nodes):
            node.connect(
                nodes[(i + 1) % len(nodes)],
                LocalSimplexConnection(framework),
                LocalSimplexConnection(framework),
            )

        await nodes[0].send_message(b"block selection")

        timeout = 15
        for _ in range(timeout):
            broadcasted_msgs = []
            for node in nodes:
                if not node.broadcast_channel.empty():
                    broadcasted_msgs.append(await node.broadcast_channel.get())

            if len(broadcasted_msgs) == 0:
                await asyncio.sleep(1)
            else:
                # We expect only one node to broadcast the message.
                assert len(broadcasted_msgs) == 1
                self.assertEqual(b"block selection", broadcasted_msgs[0])
                return
        self.fail("timeout")

    # TODO: check noise
