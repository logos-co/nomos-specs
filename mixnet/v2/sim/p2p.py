import math
import random
from collections import defaultdict

import simpy

from config import Config
from sphinx import SphinxPacket


class P2p:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.nodes = []
        self.message_sizes = []
        self.nodes_emitted_msg_around_interval = defaultdict(int)

    def add_node(self, nodes):
        self.nodes.extend(nodes)

    # TODO: This should accept only bytes, but SphinxPacket is also accepted until we implement the Sphinx serde
    def broadcast(self, sender, msg: SphinxPacket | bytes):
        self.log("Broadcasting a msg: %d bytes" % len(msg))
        self.message_sizes.append(len(msg))

        now_frac, now_int = math.modf(self.env.now)
        if now_int % self.config.message_interval == 0 and now_frac <= self.config.max_message_prep_time:
            self.nodes_emitted_msg_around_interval[sender] += 1

        # Yield 0 to ensure that the broadcast is done in the same time step.
        # Without this, SimPy complains that the broadcast func is not a generator.
        yield self.env.timeout(0)

        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.env.process(node.receive_message(msg))

    def get_nodes(self, n: int):
        return random.sample(self.nodes, n)

    def log(self, msg):
        print("P2P at %g: %s" % (self.env.now, msg))