from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.config import (
    GlobalConfig,
    MixMembership,
    NodeConfig,
    NodeInfo,
)


def init_mixnet_config(num_nodes: int) -> tuple[GlobalConfig, list[NodeConfig]]:
    transmission_rate_per_sec = 3
    max_mix_path_length = 3
    node_configs = [
        NodeConfig(X25519PrivateKey.generate(), max_mix_path_length)
        for _ in range(num_nodes)
    ]
    global_config = GlobalConfig(
        MixMembership(
            [NodeInfo(node_config.private_key) for node_config in node_configs]
        ),
        transmission_rate_per_sec,
        max_mix_path_length,
    )
    return (global_config, node_configs)
