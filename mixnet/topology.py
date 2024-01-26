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
class MixnetTopology:
    # In production, this can be a 1-D array, which is accessible by indexes.
    # Here, we use a 2-D array for readability.
    layers: List[List[MixNodeInfo]]

    def generate_route(self) -> list[MixNodeInfo]:
        return [random.choice(layer) for layer in self.layers]

    def choose_mix_destionation(self) -> MixNodeInfo:
        all_mixnodes = [mixnode for layer in self.layers for mixnode in layer]
        return random.choice(all_mixnodes)


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
