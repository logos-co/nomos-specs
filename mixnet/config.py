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
    mix_path_length: int
    gossip: GossipConfig


@dataclass
class GossipConfig:
    # The target number of peers a node should maintain in its p2p network
    peering_degree: int


@dataclass
class MixMembership:
    nodes: List[NodeInfo]

    def generate_route(self, num_hops: int, last_mix: NodeInfo) -> list[NodeInfo]:
        """
        Generate a mix route for a Sphinx packet.
        The pre-selected mix_destination is used as a last mix node in the route,
        so that associated packets can be merged together into a original message.
        """
        return [*(self.choose() for _ in range(num_hops - 1)), last_mix]

    def choose(self) -> NodeInfo:
        """
        Choose a mix node as a mix destination that will reconstruct a message from Sphinx packets.
        """
        return random.choice(self.nodes)


@dataclass
class NodeInfo:
    public_key: X25519PublicKey

    def sphinx_node(self) -> SphinxNode:
        # TODO: Use a pre-signed incentive tx, instead of NodeAddress
        dummy_node_addr = bytes(32)
        return SphinxNode(self.public_key, dummy_node_addr)
