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

    def set_nodes(self, nodes: list["Node"]):
        self.nodes = nodes

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
    def send(self, msg: SphinxPacket | bytes, sender: "Node", receiver: "Node"):
        # simulate network latency
        yield self.env.timeout(random.uniform(0, self.config.p2p.max_network_latency))
        # Measurement and adversary
        self.measurement.measure_ingress(receiver, msg)
        self.adversary.observe_incoming_message(receiver)

    def log(self, msg):
        print(f"t={self.env.now:.3f}: P2P: {msg}")


class NaiveBroadcastP2P(P2P):
    def __init__(self, env: simpy.Environment, config: Config):
        super().__init__(env, config)
        self.nodes = []

    # This should accept only bytes in practice,
    # but we accept SphinxPacket as well because we don't implement Sphinx deserialization.
    def broadcast(self, sender: "Node", msg: SphinxPacket | bytes):
        yield from super().broadcast(sender, msg)
        self.log(f"Node:{sender.id}: Broadcasting a msg: {len(msg)} bytes")
        for receiver in self.nodes:
            self.measurement.measure_egress(sender, msg)
            self.env.process(self.send(msg, sender, receiver))

    def send(self, msg: SphinxPacket | bytes, sender: "Node", receiver: "Node"):
        yield from super().send(msg, sender, receiver)
        self.env.process(receiver.receive_message(msg))


class GossipP2P(P2P):
    def __init__(self, env: simpy.Environment, config: Config):
        super().__init__(env, config)
        self.topology = defaultdict(set)
        self.message_cache = defaultdict(dict)

    def set_nodes(self, nodes: list["Node"]):
        super().set_nodes(nodes)
        for i, node in enumerate(nodes):
            # Each node is chained with the right neighbor, so that no node is not orphaned.
            # And then, each node is connected to a random subset of other nodes.
            front, back = nodes[:i], nodes[i + 1:]
            if len(back) > 0:
                neighbor = back[0]
                back = back[1:]
            elif len(front) > 0:
                neighbor = front[0]
                front = front[1:]
            else:
                continue

            others = front + back
            n = min(self.config.p2p.connection_density - 1, len(others))
            conns = set(random.sample(others, n))
            conns.add(neighbor)
            self.topology[node] = conns

    def broadcast(self, sender: "Node", msg: SphinxPacket | bytes):
        yield from super().broadcast(sender, msg)
        self.log(f"Node:{sender.id}: Gossiping a msg: {len(msg)} bytes")

        # if the msg is created originally by the sender (not forwarded from others), cache it with the sender itself.
        msg_hash = hashlib.sha256(bytes(msg)).digest()
        if msg_hash not in self.message_cache[sender]:
            self.message_cache[sender][msg_hash] = sender

        for receiver in self.topology[sender]:
            # Don't gossip the message if it was received from the node who is going to be the receiver,
            # which means that the node already knows the message.
            if receiver != self.message_cache[sender][msg_hash]:
                self.measurement.measure_egress(sender, msg)
                self.env.process(self.send(msg, sender, receiver))

    def send(self, msg: SphinxPacket | bytes, sender: "Node", receiver: "Node"):
        yield from super().send(msg, sender, receiver)
        # Receive/gossip the msg only if it hasn't been received before.
        # i.e. each message is received/gossiped at most once by each node.
        msg_hash = hashlib.sha256(bytes(msg)).digest()
        if msg_hash not in self.message_cache[receiver]:
            self.message_cache[receiver][msg_hash] = sender
            self.env.process(receiver.receive_message(msg))
            self.env.process(self.broadcast(receiver, msg))
