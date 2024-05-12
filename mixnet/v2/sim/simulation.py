import simpy

from node import Node
from p2p import P2p


class Simulation:
    def __init__(self):
        self.env = simpy.Environment()
        self.p2p = P2p(self.env)
        self.nodes = [Node(i, self.env, self.p2p) for i in range(2)]
        self.p2p.add_node(self.nodes)

    def run(self, until):
        self.env.run(until=until)
