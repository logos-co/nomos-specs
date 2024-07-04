import asyncio
import random
import time

from mixnet.config import GlobalConfig, MixMembership, NodeInfo
from mixnet.node import Node
from mixnet.sim.config import Config
from mixnet.sim.connection import MeteredRemoteSimplexConnection
from mixnet.sim.stats import ConnectionStats


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config

    async def run(self):
        nodes, conn_measurement = self.init_nodes()

        deadline = time.time() + self.config.simulation.scaled_duration()
        tasks: list[asyncio.Task] = []
        for node in nodes:
            tasks.append(asyncio.create_task(self.run_logic(node, deadline)))
        await asyncio.gather(*tasks)

        conn_measurement.bandwidths()

    def init_nodes(self) -> tuple[list[Node], ConnectionStats]:
        node_configs = self.config.mixnet.node_configs()
        global_config = GlobalConfig(
            MixMembership(
                [
                    NodeInfo(node_config.private_key.public_key())
                    for node_config in node_configs
                ]
            ),
            self.config.simulation.scale_rate(
                self.config.mixnet.transmission_rate_per_sec
            ),
            self.config.mixnet.max_mix_path_length,
        )
        nodes = [Node(node_config, global_config) for node_config in node_configs]

        conn_stats = ConnectionStats()
        for i, node in enumerate(nodes):
            inbound_conn, outbound_conn = self.create_conn(), self.create_conn()
            peer = nodes[(i + 1) % len(nodes)]
            node.connect(peer, inbound_conn, outbound_conn)
            conn_stats.register(node, inbound_conn, outbound_conn)
            conn_stats.register(peer, outbound_conn, inbound_conn)

        return nodes, conn_stats

    def create_conn(self) -> MeteredRemoteSimplexConnection:
        return MeteredRemoteSimplexConnection(self.config.simulation)

    async def run_logic(self, node: Node, deadline: float):
        while time.time() < deadline:
            await asyncio.sleep(
                self.config.simulation.scale_time(
                    self.config.logic.lottery_interval_sec
                )
            )

            if random.random() < self.config.logic.sender_prob:
                await node.send_message(b"selected block")
