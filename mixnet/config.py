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


@dataclass
class MixnetConfig:
    emission_rate_per_min: int  # Poisson rate parameter: lambda
    redundancy: int
    delay_rate_per_min: int  # Poisson rate parameter: mu
    topology: MixnetTopology


@dataclass
class MixnetTopology:
    # In production, this can be a 1-D array, which is accessible by indexes.
    # Here, we use a 2-D array for readability.
    layers: List[List[MixNodeInfo]]

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
