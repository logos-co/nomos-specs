from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.config import (
    MixMembership,
    MixnetConfig,
    NodeConfig,
    NodeInfo,
)


def init_mixnet_config(num_nodes: int) -> MixnetConfig:
    transmission_rate_per_sec = 3
    node_configs = [
        NodeConfig(X25519PrivateKey.generate(), transmission_rate_per_sec)
        for _ in range(num_nodes)
    ]
    membership = MixMembership(
        [NodeInfo(node_config.private_key) for node_config in node_configs]
    )
    return MixnetConfig(node_configs, membership)
