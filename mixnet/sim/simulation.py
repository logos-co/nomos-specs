import usim
from matplotlib import pyplot

import mixnet.framework.usim as usimfw
from mixnet.config import GlobalConfig, MixMembership, NodeInfo
from mixnet.framework import Framework
from mixnet.node import Node, PeeringDegreeReached
from mixnet.sim.config import Config
from mixnet.sim.connection import MeteredRemoteSimplexConnection
from mixnet.sim.state import NodeState, NodeStateTable
from mixnet.sim.stats import ConnectionStats


class Simulation:
    """
    Manages the entire cycle of simulation: initialization, running, and analysis.
    """

    def __init__(self, config: Config):
        self.config = config

    async def run(self):
        # Run the simulation
        conn_stats, node_state_table = await self.__run()
        # Analyze the simulation results
        conn_stats.analyze()
        node_state_table.analyze()
        # Show plots
        if self.config.simulation.show_plots:
            pyplot.show()

    async def __run(self) -> tuple[ConnectionStats, NodeStateTable]:
        # Initialize analysis tools
        node_state_table = NodeStateTable(
            self.config.network.num_nodes, self.config.simulation.duration_sec
        )
        conn_stats = ConnectionStats()

        # Create a μSim scope and run the simulation
        async with usim.until(usim.time + self.config.simulation.duration_sec) as scope:
            self.framework = usimfw.Framework(scope)
            nodes, conn_stats, node_state_table = self.__init_nodes(
                node_state_table, conn_stats
            )
            for node in nodes:
                self.framework.spawn(self.__run_node_logic(node))

        # Return analysis tools once the μSim scope is done
        return conn_stats, node_state_table

    def __init_nodes(
        self, node_state_table: NodeStateTable, conn_stats: ConnectionStats
    ) -> tuple[list[Node], ConnectionStats, NodeStateTable]:
        # Initialize node/global configurations
        node_configs = self.config.node_configs()
        global_config = GlobalConfig(
            MixMembership(
                [
                    NodeInfo(node_config.private_key.public_key())
                    for node_config in node_configs
                ],
                self.config.mix.mix_path.seed,
            ),
            self.config.mix.transmission_rate_per_sec,
            self.config.mix.max_message_size,
            self.config.mix.mix_path.max_length,
        )

        # Initialize Node instances
        nodes = [
            Node(self.framework, node_config, global_config)
            for node_config in node_configs
        ]

        # Connect nodes to each other
        for i, node in enumerate(nodes):
            # For now, we only consider a simple ring topology for simplicity.
            peer_idx = (i + 1) % len(nodes)
            peer = nodes[peer_idx]
            node_states = node_state_table[i]
            peer_states = node_state_table[peer_idx]

            # Create simplex inbound/outbound connections
            # and use them to connect node and peer.
            inbound_conn, outbound_conn = (
                self.__create_conn(peer_states, node_states),
                self.__create_conn(node_states, peer_states),
            )
            node.connect(peer, inbound_conn, outbound_conn)
            # Register the connections to the connection statistics
            conn_stats.register(node, inbound_conn, outbound_conn)
            conn_stats.register(peer, outbound_conn, inbound_conn)

        return nodes, conn_stats, node_state_table

    def __create_conn(
        self, sender_states: list[NodeState], receiver_states: list[NodeState]
    ) -> MeteredRemoteSimplexConnection:
        return MeteredRemoteSimplexConnection(
            self.config.network,
            self.framework,
            sender_states,
            receiver_states,
        )

    async def __run_node_logic(self, node: Node):
        """
        Runs the lottery periodically to check if the node is selected to send a block.
        If the node is selected, creates a block and sends it through mix nodes.
        """
        lottery_config = self.config.logic.sender_lottery
        while True:
            await (usim.time + lottery_config.interval_sec)
            if lottery_config.seed.random() < lottery_config.probability:
                await node.send_message(b"selected block")
