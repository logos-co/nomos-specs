from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import List

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from pysphinx.sphinx import Node as SphinxNode


@dataclass
class GlobalConfig:
    """
    Global parameters used across all nodes in the network
    """

    membership: MixMembership
    transmission_rate_per_sec: int  # Global Transmission Rate
    max_message_size: int
    max_mix_path_length: int


@dataclass
class NodeConfig:
    """
    Node-specific parameters
    """

    private_key: X25519PrivateKey
    mix_path_length: int
    nomssip: NomssipConfig


@dataclass
class NomssipConfig:
    # The target number of peers a node should maintain in its p2p network
    peering_degree: int


@dataclass
class MixMembership:
    """
    A list of public information of nodes in the network.
    We assume that this list is known to all nodes in the network.
    """

    nodes: List[NodeInfo]
    rng: random.Random = field(default_factory=random.Random)

    def generate_route(self, length: int) -> list[NodeInfo]:
        """
        Choose `length` nodes with replacement as a mix route.
        """
        return self.rng.choices(self.nodes, k=length)


@dataclass
class NodeInfo:
    """
    Public information of a node to be shared to all nodes in the network
    """

    public_key: X25519PublicKey

    def sphinx_node(self) -> SphinxNode:
        dummy_node_addr = bytes(32)
        return SphinxNode(self.public_key, dummy_node_addr)
