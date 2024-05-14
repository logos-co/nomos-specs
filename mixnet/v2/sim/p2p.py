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

        yield self.env.timeout(1)
        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.env.process(node.receive_message(msg))

    def get_nodes(self, n: int):
        return random.sample(self.nodes, n)

    def log(self, msg):
        print("P2P at %d: %s" % (self.env.now, msg))