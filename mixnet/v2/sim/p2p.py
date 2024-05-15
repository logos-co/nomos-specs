import random

import simpy

from sphinx import SphinxPacket


class P2p:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.nodes = []
        self.message_sizes = []

    def add_node(self, nodes):
        self.nodes.extend(nodes)

    # TODO: This should accept only bytes, but SphinxPacket is also accepted until we implement the Sphinx serde
    def broadcast(self, msg: SphinxPacket | bytes):
        self.log("Broadcasting a msg: %d bytes" % len(msg))
        self.message_sizes.append(len(msg))

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