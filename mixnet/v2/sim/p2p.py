from __future__ import annotations
import random
from typing import TYPE_CHECKING

import simpy

from adversary import Adversary
from config import Config
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node


class P2p:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.nodes = []
        self.adversary = Adversary(env, config)

    def add_node(self, nodes: list["Node"]):
        self.nodes.extend(nodes)

    def get_nodes(self, n: int) -> list["Node"]:
        return random.sample(self.nodes, n)

    # This should accept only bytes in practice,
    # but we accept SphinxPacket as well because we don't implement Sphinx deserialization.
    def broadcast(self, sender, msg: SphinxPacket | bytes):
        self.log("Broadcasting a msg: %d bytes" % len(msg))

        # Adversary
        self.adversary.inspect_message_size(msg)
        self.adversary.observe_outgoing_message(sender)

        # Yield 0 to ensure that the broadcast is done in the same time step.
        # Without any yield, SimPy complains that the broadcast func is not a generator.
        yield self.env.timeout(0)

        # TODO: gossipsub or something similar
        for node in self.nodes:
            self.env.process(self.send(msg, node))

    def send(self, msg: SphinxPacket | bytes, node):
        # simulate network latency
        yield self.env.timeout(random.uniform(0, self.config.p2p.max_network_latency))

        self.adversary.observe_incoming_message(node)
        self.env.process(node.receive_message(msg))

    def log(self, msg):
        print("P2P at %g: %s" % (self.env.now, msg))
