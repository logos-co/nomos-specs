from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from pysphinx.node import Node

from mixnet.bls import BlsPrivateKey, BlsPublicKey
from mixnet.fisheryates import FisherYates


@dataclass
class MixnetConfig:
    topology_config: MixnetTopologyConfig
    mixclient_config: MixClientConfig
    mixnode_config: MixNodeConfig


@dataclass
class MixnetTopologyConfig:
    mixnode_candidates: List[MixNodeInfo]
    size: MixnetTopologySize
    entropy: bytes


@dataclass
class MixClientConfig:
    emission_rate_per_min: int  # Poisson rate parameter: lambda
    redundancy: int
    topology: MixnetTopology


@dataclass
class MixNodeConfig:
    encryption_private_key: X25519PrivateKey
    delay_rate_per_min: int  # Poisson rate parameter: mu


@dataclass
class MixnetTopology:
    # In production, this can be a 1-D array, which is accessible by indexes.
    # Here, we use a 2-D array for readability.
    layers: List[List[MixNodeInfo]]

    def __init__(
        self,
        config: MixnetTopologyConfig,
    ) -> None:
        """
        Build a new topology deterministically using an entropy and a given set of candidates.
        """
        shuffled = FisherYates.shuffle(config.mixnode_candidates, config.entropy)
        sampled = shuffled[: config.size.num_total_mixnodes()]

        layers = []
        for layer_id in range(config.size.num_layers):
            start = layer_id * config.size.num_mixnodes_per_layer
            layer = sampled[start : start + config.size.num_mixnodes_per_layer]
            layers.append(layer)
        self.layers = layers

    def generate_route(self, mix_destination: MixNodeInfo) -> list[MixNodeInfo]:
        """
        Generate a mix route for a Sphinx packet.
        The pre-selected mix_destination is used as a last mix node in the route,
        so that associated packets can be merged together into a original message.
        """
        route = [random.choice(layer) for layer in self.layers[:-1]]
        route.append(mix_destination)
        return route

    def choose_mix_destination(self) -> MixNodeInfo:
        """
        Choose a mix node from the last mix layer as a mix destination
        that will reconstruct a message from Sphinx packets.
        """
        return random.choice(self.layers[-1])


@dataclass
class MixnetTopologySize:
    num_layers: int
    num_mixnodes_per_layer: int

    def num_total_mixnodes(self) -> int:
        return self.num_layers * self.num_mixnodes_per_layer


# 32-byte that represents an IP address and a port of a mix node.
NodeAddress: TypeAlias = bytes


@dataclass
class MixNodeInfo:
    identity_private_key: BlsPrivateKey
    encryption_private_key: X25519PrivateKey
    addr: NodeAddress

    def identity_public_key(self) -> BlsPublicKey:
        return self.identity_private_key.get_g1()

    def encryption_public_key(self) -> X25519PublicKey:
        return self.encryption_private_key.public_key()

    def sphinx_node(self) -> Node:
        return Node(self.encryption_private_key, self.addr)
