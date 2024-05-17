import math
import random
from collections import defaultdict

import simpy
from simpy.core import SimTime

from config import Config
from sphinx import SphinxPacket


class P2p:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.nodes = []
        # The followings are for an adversary.
        # TODO: Move these to a separate class `Adversary`.
        self.message_sizes = []
        self.senders_around_interval = defaultdict(int)
        self.mixed_msgs_per_window = []
        self.env.process(self.update_observation_window())

    def add_node(self, nodes):
        self.nodes.extend(nodes)

    def get_nodes(self, n: int):
        return random.sample(self.nodes, n)

    # This should accept only bytes in practice,
    # but we accept SphinxPacket as well because we don't implement Sphinx deserialization.
    def broadcast(self, sender, msg: SphinxPacket | bytes):
        self.log("Broadcasting a msg: %d bytes" % len(msg))

        # Adversary
        self.message_sizes.append(len(msg))
        self.mixed_msgs_per_window[-1][sender] -= 1
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval[sender] += 1

        # Yield 0 to ensure that the broadcast is done in the same time step.
        # Without any yield, SimPy complains that the broadcast func is not a generator.
        yield self.env.timeout(0)

        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.env.process(self.send(msg, node))

    def send(self, msg: SphinxPacket | bytes, node):
        # simulate network latency
        yield self.env.timeout(random.uniform(0, self.config.max_network_latency))

        self.mixed_msgs_per_window[-1][node] += 1
        self.env.process(node.receive_message(msg))

    # TODO: Move to a separate class `Adversary`.
    def is_around_message_interval(self, time: SimTime):
        now_frac, now_int = math.modf(time)
        return now_int % self.config.message_interval == 0 and now_frac <= self.config.max_message_prep_time

    # TODO: Move to a separate class `Adversary`.
    def update_observation_window(self):
        while True:
            self.mixed_msgs_per_window.append(defaultdict(int))
            yield self.env.timeout(self.config.io_observation_window)

    def log(self, msg):
        print("P2P at %g: %s" % (self.env.now, msg))