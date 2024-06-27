import asyncio
import random

from mixnet.config import MixMembership, NodeInfo
from mixnet.node import Node
from mixnet.sim.config import Config


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config

    async def run(self):
        # Initialize mixnet nodes and establish connections
        node_configs = self.config.mixnet.node_configs()
        membership = MixMembership(
            [NodeInfo(node_config.private_key) for node_config in node_configs]
        )
        nodes = [Node(node_config, membership) for node_config in node_configs]
        for i, node in enumerate(nodes):
            node.connect(nodes[(i + 1) % len(nodes)])

        await asyncio.sleep(self.config.simulation.duration_sec)
