import random

import simpy

from config import Config
from node import Node
from p2p import NaiveBroadcastP2P


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config
        self.env = simpy.Environment()
        self.p2p = NaiveBroadcastP2P(self.env, config)
        self.nodes = [Node(i, self.env, self.p2p, config) for i in range(config.mixnet.num_nodes)]
        self.p2p.add_node(self.nodes)

    def run(self):
        self.env.run(until=self.config.simulation.running_time)
