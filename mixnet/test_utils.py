from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.config import (
    GlobalConfig,
    MixMembership,
    NodeConfig,
    NodeInfo,
    NomssipConfig,
)


def init_mixnet_config(
    num_nodes: int,
    max_message_size: int = 512,
    max_mix_path_length: int = 3,
) -> tuple[GlobalConfig, list[NodeConfig], dict[bytes, X25519PrivateKey]]:
    gossip_config = NomssipConfig(peering_degree=6)
    node_configs = [
        NodeConfig(X25519PrivateKey.generate(), max_mix_path_length, gossip_config)
        for _ in range(num_nodes)
    ]
    global_config = GlobalConfig(
        MixMembership(
            [
                NodeInfo(node_config.private_key.public_key())
                for node_config in node_configs
            ]
        ),
        transmission_rate_per_sec=3,
        max_message_size=max_message_size,
        max_mix_path_length=max_mix_path_length,
    )
    key_map = {
        node_config.private_key.public_key().public_bytes_raw(): node_config.private_key
        for node_config in node_configs
    }
    return (global_config, node_configs, key_map)
