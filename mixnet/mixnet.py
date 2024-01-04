from dataclasses import dataclass
from typing import List, Self, Tuple, TypeAlias

from bls import BlsPrivateKey, BlsPublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import (X25519PrivateKey,
                                                              X25519PublicKey)
from fisheryates import FisherYates

NodeId: TypeAlias = BlsPublicKey
SocketAddr: TypeAlias = Tuple[str, int]


@dataclass
class MixNode:
    identity_public_key: BlsPublicKey
    encryption_public_key: X25519PublicKey
    addr: SocketAddr

    @classmethod
    def build(
        cls,
        identity_private_key: BlsPrivateKey,
        encryption_private_key: X25519PrivateKey,
        addr: SocketAddr,
    ) -> Self:
        return cls(
            identity_private_key.get_g1(),
            encryption_private_key.public_key(),
            addr,
        )


@dataclass
class MixnetTopology:
    layers: List[List[MixNode]]


@dataclass
class Mixnet:
    mix_nodes: List[MixNode]

    def build_topology(
        self,
        entropy: bytes,
        n_layers: int,
        n_nodes_per_layer: int,
    ) -> MixnetTopology:
        assert n_nodes_per_layer * n_layers < len(self.mix_nodes)

        shuffled = FisherYates.shuffle(self.mix_nodes, entropy)
        sampled = shuffled[: n_nodes_per_layer * n_layers]
        layers = []
        for l in range(n_layers):
            start = l * n_nodes_per_layer
            layer = sampled[start : start + n_nodes_per_layer]
            layers.append(layer)
        return MixnetTopology(layers)
