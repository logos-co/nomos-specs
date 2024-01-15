from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from pysphinx.node import Node

from mixnet.bls import BlsPrivateKey, BlsPublicKey

NodeId: TypeAlias = BlsPublicKey
# 32-byte that represents an IP address and a port of a mix node.
NodeAddress: TypeAlias = bytes


@dataclass
class MixNode:
    identity_private_key: BlsPrivateKey
    encryption_private_key: X25519PrivateKey
    addr: NodeAddress

    def identity_public_key(self) -> BlsPublicKey:
        return self.identity_private_key.get_g1()

    def encryption_public_key(self) -> X25519PublicKey:
        return self.encryption_private_key.public_key()

    def sphinx_node(self) -> Node:
        return Node(self.encryption_private_key, self.addr)
