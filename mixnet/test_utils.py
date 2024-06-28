from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.config import (
    GlobalConfig,
    MixMembership,
    NodeConfig,
    NodeInfo,
)


def init_mixnet_config(
    num_nodes: int,
) -> tuple[GlobalConfig, list[NodeConfig], dict[bytes, X25519PrivateKey]]:
    transmission_rate_per_sec = 3
    peering_degree = 6
    max_mix_path_length = 3
    node_configs = [
        NodeConfig(X25519PrivateKey.generate(), peering_degree, max_mix_path_length)
        for _ in range(num_nodes)
    ]
    global_config = GlobalConfig(
        MixMembership(
            [
                NodeInfo(node_config.private_key.public_key())
                for node_config in node_configs
            ]
        ),
        transmission_rate_per_sec,
        max_mix_path_length,
    )
    key_map = {
        node_config.private_key.public_key().public_bytes_raw(): node_config.private_key
        for node_config in node_configs
    }
    return (global_config, node_configs, key_map)
