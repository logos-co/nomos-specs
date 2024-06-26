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
class MixnetConfig:
    node_configs: List[NodeConfig]
    membership: MixMembership


@dataclass
class NodeConfig:
    private_key: X25519PrivateKey
    conn_degree: int  # Connection Degree (default: 6)
    transmission_rate_per_sec: int  # Global Transmission Rate


@dataclass
class MixMembership:
    nodes: List[NodePublicInfo]

    def generate_route(
        self, num_hops: int, last_mix: NodePublicInfo
    ) -> list[NodePublicInfo]:
        """
        Generate a mix route for a Sphinx packet.
        The pre-selected mix_destination is used as a last mix node in the route,
        so that associated packets can be merged together into a original message.
        """
        route = [self.choose() for _ in range(num_hops - 1)]
        route.append(last_mix)
        return route

    def choose(self) -> NodePublicInfo:
        """
        Choose a mix node as a mix destination that will reconstruct a message from Sphinx packets.
        """
        return random.choice(self.nodes)


@dataclass
class NodePublicInfo:
    private_key: X25519PrivateKey

    def encryption_public_key(self) -> X25519PublicKey:
        return self.private_key.public_key()

    def sphinx_node(self) -> SphinxNode:
        return SphinxNode(self.private_key, bytes(32))
