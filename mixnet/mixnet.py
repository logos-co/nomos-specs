from __future__ import annotations

from dataclasses import dataclass
from typing import List, Self, TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (X25519PrivateKey,
                                                              X25519PublicKey)

from mixnet.bls import BlsPrivateKey, BlsPublicKey
from mixnet.fisheryates import FisherYates

NodeId: TypeAlias = BlsPublicKey
# 32-byte that represents an IP address and a port of a mix node.
NodeAddress: TypeAlias = bytes


@dataclass
class Mixnet:
    mix_nodes: List[MixNode]

    # Build a new topology deterministically using an entropy.
    # The entropy is expected to be injected from outside.
    #
    # TODO: Implement constructing a new topology in advance to minimize the topology transition time.
    #       https://www.notion.so/Mixnet-Specification-807b624444a54a4b88afa1cc80e100c2?pvs=4#9a7f6089e210454bb11fe1c10fceff68
    def build_topology(
        self,
        entropy: bytes,
        n_layers: int,
        n_nodes_per_layer: int,
    ) -> MixnetTopology:
        num_nodes = n_nodes_per_layer * n_layers
        assert num_nodes < len(self.mix_nodes)

        sampled = FisherYates.sample(self.mix_nodes, num_nodes, entropy)
        layers = []
        for l in range(n_layers):
            start = l * n_nodes_per_layer
            layer = sampled[start : start + n_nodes_per_layer]
            layers.append(layer)
        return MixnetTopology(layers)


@dataclass
class MixNode:
    identity_public_key: BlsPublicKey
    encryption_public_key: X25519PublicKey
    addr: NodeAddress

    def __init__(
        self,
        identity_private_key: BlsPrivateKey,
        encryption_private_key: X25519PrivateKey,
        addr: NodeAddress,
    ):
        self.identity_public_key = identity_private_key.get_g1()
        self.encryption_public_key = encryption_private_key.public_key()
        self.addr = addr


@dataclass
class MixnetTopology:
    layers: List[List[MixNode]]
