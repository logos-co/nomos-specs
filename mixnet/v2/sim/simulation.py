import simpy

from mixnet.v2.sim.node import Node
from mixnet.v2.sim.p2p import P2p


class Simulation:
    def __init__(self):
        self.env = simpy.Environment()
        self.p2p = P2p(self.env)
        self.nodes = [Node(str(i), self.env, self.p2p) for i in range(2)]
        self.p2p.add_node(self.nodes)

    def run(self, until):
        self.env.run(until=until)
