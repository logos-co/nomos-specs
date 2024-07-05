import usim

import mixnet.framework.usim as usimfw
from mixnet.config import GlobalConfig, MixMembership, NodeInfo
from mixnet.framework.framework import Framework
from mixnet.node import Node, PeeringDegreeReached
from mixnet.sim.config import Config
from mixnet.sim.connection import MeteredRemoteSimplexConnection
from mixnet.sim.state import AllNodeStates, NodeState
from mixnet.sim.stats import ConnectionStats


class Simulation:
    config: Config
    framework: Framework

    def __init__(self, config: Config):
        self.config = config

    async def run(self):
        conn_stats, all_node_states = await self._run()
        conn_stats.bandwidths()
        all_node_states.analyze()

    async def _run(self) -> tuple[ConnectionStats, AllNodeStates]:
        async with usim.until(usim.time + self.config.simulation.duration_sec) as scope:
            self.framework = usimfw.Framework(scope)
            nodes, conn_stats, all_node_states = self.init_nodes()
            for node in nodes:
                self.framework.spawn(self.run_logic(node))
            return conn_stats, all_node_states
        assert False  # unreachable

    def init_nodes(self) -> tuple[list[Node], ConnectionStats, AllNodeStates]:
        node_configs = self.config.mixnet.node_configs()
        global_config = GlobalConfig(
            MixMembership(
                [
                    NodeInfo(node_config.private_key.public_key())
                    for node_config in node_configs
                ],
                self.config.mixnet.mix_path.seed,
            ),
            self.config.mixnet.transmission_rate_per_sec,
            self.config.mixnet.mix_path.max_length,
        )
        nodes = [
            Node(self.framework, node_config, global_config)
            for node_config in node_configs
        ]

        all_node_states = AllNodeStates(len(nodes), self.config.simulation.duration_sec)
        conn_stats = ConnectionStats()
        for i, node in enumerate(nodes):
            peer_idx = (i + 1) % len(nodes)
            peer = nodes[peer_idx]
            node_states = all_node_states[i]
            peer_states = all_node_states[peer_idx]

            inbound_conn, outbound_conn = (
                self.create_conn(peer_states, node_states),
                self.create_conn(node_states, peer_states),
            )
            try:
                node.connect(peer, inbound_conn, outbound_conn)
            except PeeringDegreeReached:
                continue
            conn_stats.register(node, inbound_conn, outbound_conn)
            conn_stats.register(peer, outbound_conn, inbound_conn)

        return nodes, conn_stats, all_node_states

    def create_conn(
        self, sender_states: list[NodeState], receiver_states: list[NodeState]
    ) -> MeteredRemoteSimplexConnection:
        return MeteredRemoteSimplexConnection(
            self.config.simulation.network,
            self.framework,
            sender_states,
            receiver_states,
        )

    async def run_logic(self, node: Node):
        lottery_config = self.config.logic.sender_lottery
        while True:
            await (usim.time + lottery_config.interval_sec)
            if lottery_config.seed.random() < lottery_config.probability:
                await node.send_message(b"selected block")
