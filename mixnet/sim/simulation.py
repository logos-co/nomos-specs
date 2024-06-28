import asyncio
import random

from mixnet.config import GlobalConfig, MixMembership, NodeInfo
from mixnet.node import Node
from mixnet.sim.config import Config


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config

    async def run(self):
        # Initialize mixnet nodes and establish connections
        node_configs = self.config.mixnet.node_configs()
        global_config = GlobalConfig(
            MixMembership(
                [
                    NodeInfo(node_config.private_key.public_key())
                    for node_config in node_configs
                ]
            ),
            self.config.mixnet.transmission_rate_per_sec,
            self.config.mixnet.max_mix_path_length,
        )
        nodes = [Node(node_config, global_config) for node_config in node_configs]
        for i, node in enumerate(nodes):
            node.connect(nodes[(i + 1) % len(nodes)])

        await asyncio.sleep(self.config.simulation.duration_sec)
