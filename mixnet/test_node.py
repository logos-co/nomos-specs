from unittest import IsolatedAsyncioTestCase

from mixnet.node import Node
from mixnet.test_utils import (
    init_mixnet_config,
)


class TestNode(IsolatedAsyncioTestCase):
    async def test_node(self):
        config = init_mixnet_config(10)
        nodes = [
            Node(node_config, config.membership) for node_config in config.node_configs
        ]
        await nodes[0].send_message(b"block selection")
