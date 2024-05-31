import random

import simpy

from config import Config, P2PConfig
from node import Node
from p2p import NaiveBroadcastP2P, GossipP2P


class Simulation:
    def __init__(self, config: Config):
        random.seed()
        self.config = config
        self.env = simpy.Environment()
        self.p2p = Simulation.init_p2p(self.env, config)
        nodes = [Node(i, self.env, self.p2p, config, self.p2p.measurement) for i in range(config.mixnet.num_nodes)]
        self.p2p.set_nodes(nodes)

    def run(self):
        self.env.run(until=self.config.simulation.running_time)

    @classmethod
    def init_p2p(cls, env: simpy.Environment, config: Config):
        match config.p2p.type:
            case P2PConfig.TYPE_ONE_TO_ALL:
                return NaiveBroadcastP2P(env, config)
            case P2PConfig.TYPE_GOSSIP:
                return GossipP2P(env, config)
            case _:
                raise ValueError("Unknown P2P type")