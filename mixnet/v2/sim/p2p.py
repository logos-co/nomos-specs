from mixnet.v2.sim.node import Node
from mixnet.v2.sim.simulation import Simulation


class P2p:
    def __init__(self, sim: Simulation, nodes: list[Node]):
        self.sim = sim
        self.nodes = nodes

    def broadcast(self, msg):
        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.sim.env.process(node.receive_message(msg))
