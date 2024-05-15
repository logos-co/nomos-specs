import random

import simpy

from config import Config
from node import Node
from p2p import P2p


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config
        self.env = simpy.Environment()
        self.p2p = P2p(self.env, config)
        self.nodes = [Node(i, self.env, self.p2p, config) for i in range(config.num_nodes)]
        self.p2p.add_node(self.nodes)

    def run(self):
        self.env.run(until=self.config.running_time)
