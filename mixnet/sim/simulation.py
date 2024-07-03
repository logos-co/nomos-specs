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

        deadline = time.time() + self.scaled_time(self.config.simulation.duration_sec)
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
            self.scaled_rate(self.config.mixnet.transmission_rate_per_sec),
            self.config.mixnet.max_mix_path_length,
        )
        nodes = [Node(node_config, global_config) for node_config in node_configs]

        conn_stats = ConnectionStats()
        for i, node in enumerate(nodes):
            inbound_conn, outbound_conn = self.create_conn(), self.create_conn()
            node.connect(nodes[(i + 1) % len(nodes)], inbound_conn, outbound_conn)
            conn_stats.register(node, inbound_conn, outbound_conn)

        return nodes, conn_stats

    def create_conn(self) -> MeteredRemoteSimplexConnection:
        return MeteredRemoteSimplexConnection(
            latency=self.scaled_time(self.config.simulation.net_latency_sec),
            meter_interval=self.scaled_time(self.config.simulation.meter_interval_sec),
        )

    async def run_logic(self, node: Node, deadline: float):
        while time.time() < deadline:
            await asyncio.sleep(
                self.scaled_time(self.config.logic.lottery_interval_sec)
            )

            if random.random() < self.config.logic.sender_prob:
                await node.send_message(b"selected block")

    def scaled_time(self, time: float) -> float:
        return time * self.config.simulation.time_scale

    def scaled_rate(self, rate: int) -> float:
        return float(rate / self.config.simulation.time_scale)
