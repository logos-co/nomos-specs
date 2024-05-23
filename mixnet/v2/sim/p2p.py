from __future__ import annotations

import hashlib
import random
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING

import simpy

from adversary import Adversary
from config import Config
from measurement import Measurement
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node


class P2P(ABC):
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.nodes = []
        self.measurement = Measurement(env, config)
        self.adversary = Adversary(env, config)

    def add_node(self, nodes: list["Node"]):
        self.nodes.extend(nodes)

    def get_nodes(self, n: int) -> list["Node"]:
        return random.sample(self.nodes, n)

    # This should accept only bytes in practice,
    # but we accept SphinxPacket as well because we don't implement Sphinx deserialization.
    @abstractmethod
    def broadcast(self, sender: "Node", msg: SphinxPacket | bytes):
        # Adversary
        self.adversary.inspect_message_size(msg)
        self.adversary.observe_outgoing_message(sender)
        # Yield 0 to ensure that the broadcast is done in the same time step.
        # Without any yield, SimPy complains that the broadcast func is not a generator.
        yield self.env.timeout(0)

    @abstractmethod
    def send(self, msg: SphinxPacket | bytes, receiver: "Node"):
        # simulate network latency
        yield self.env.timeout(random.uniform(0, self.config.p2p.max_network_latency))
        # Measurement and adversary
        self.measurement.measure_ingress(receiver, msg)
        self.adversary.observe_incoming_message(receiver)

    def log(self, msg):
        print("P2P at %g: %s" % (self.env.now, msg))


class NaiveBroadcastP2P(P2P):
    def __init__(self, env: simpy.Environment, config: Config):
        super().__init__(env, config)

    # This should accept only bytes in practice,
    # but we accept SphinxPacket as well because we don't implement Sphinx deserialization.
    def broadcast(self, sender: "Node", msg: SphinxPacket | bytes):
        yield from super().broadcast(sender, msg)
        self.log("Broadcasting a msg: %d bytes" % len(msg))
        for node in self.nodes:
            self.measurement.measure_egress(sender, msg)
            self.env.process(self.send(msg, node))

    def send(self, msg: SphinxPacket | bytes, receiver: "Node"):
        yield from super().send(msg, receiver)
        self.env.process(receiver.receive_message(msg))


class GossipP2P(P2P):
    def __init__(self, env: simpy.Environment, config: Config):
        super().__init__(env, config)
        self.topology = defaultdict(set)
        self.message_cache = defaultdict(set)

    def broadcast(self, sender: "Node", msg: SphinxPacket | bytes):
        yield from super().broadcast(sender, msg)
        self.log("Gossiping a msg: %d bytes" % len(msg))
        for receiver in self.topology[sender]:
            self.measurement.measure_egress(sender, msg)
            self.env.process(self.send(msg, receiver))

    def send(self, msg: SphinxPacket | bytes, receiver: "Node"):
        yield from super().send(msg, receiver)
        # receive the msg only if it hasn't been received before
        msg_hash = hashlib.sha256(bytes(msg)).digest()
        if msg_hash not in self.message_cache[receiver]:
            self.message_cache[receiver].add(msg_hash)
            self.env.process(receiver.receive_message(msg))
