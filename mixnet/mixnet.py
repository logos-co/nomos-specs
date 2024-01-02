from dataclasses import dataclass
from typing import Self, TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (X25519PrivateKey,
                                                              X25519PublicKey)
from fisheryates import FisherYates

NodeId: TypeAlias = X25519PublicKey
SocketAddr: TypeAlias = tuple[str, int]


@dataclass
class MixNode:
    id: NodeId
    public_key: X25519PublicKey
    addr: SocketAddr

    @classmethod
    def build(cls, private_key: X25519PrivateKey, addr: SocketAddr) -> Self:
        public_key = private_key.public_key()
        return cls(id=public_key, public_key=public_key, addr=addr)


@dataclass
class MixnetTopology:
    layers: list[list[MixNode]]


@dataclass
class Mixnet:
    mix_nodes: list[MixNode]

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
