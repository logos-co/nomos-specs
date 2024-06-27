from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from pysphinx.sphinx import Node as SphinxNode


@dataclass
class GlobalConfig:
    membership: MixMembership
    transmission_rate_per_sec: int  # Global Transmission Rate
    # TODO: use this to make the size of Sphinx packet constant
    max_mix_path_length: int


@dataclass
class NodeConfig:
    private_key: X25519PrivateKey
    mix_path_length: int  # TODO: use this when creating Sphinx packets


@dataclass
class MixMembership:
    nodes: List[NodeInfo]

    def generate_route(self, num_hops: int, last_mix: NodeInfo) -> list[NodeInfo]:
        """
        Generate a mix route for a Sphinx packet.
        The pre-selected mix_destination is used as a last mix node in the route,
        so that associated packets can be merged together into a original message.
        """
        route = [self.choose() for _ in range(num_hops - 1)]
        route.append(last_mix)
        return route

    def choose(self) -> NodeInfo:
        """
        Choose a mix node as a mix destination that will reconstruct a message from Sphinx packets.
        """
        return random.choice(self.nodes)


@dataclass
class NodeInfo:
    private_key: X25519PrivateKey

    def public_key(self) -> X25519PublicKey:
        return self.private_key.public_key()

    def sphinx_node(self) -> SphinxNode:
        # TODO: Use a pre-signed incentive tx, instead of NodeAddress
        dummy_node_addr = bytes(32)
        return SphinxNode(self.private_key, dummy_node_addr)
