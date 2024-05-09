import random

import simpy


class P2p:
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.nodes = []

    def add_node(self, nodes):
        self.nodes.extend(nodes)

    def broadcast(self, msg):
        print("Broadcasting a message at time %d" % self.env.now)
        yield self.env.timeout(1)
        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.env.process(node.receive_message(msg))

    def get_nodes(self, n: int):
        return random.choices(self.nodes, k=n)
