import asyncio

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.config import (
    MixMembership,
    MixnetConfig,
    NodeConfig,
    NodePublicInfo,
)


def with_test_timeout(t):
    def wrapper(coroutine):
        async def run(*args, **kwargs):
            async with asyncio.timeout(t):
                return await coroutine(*args, **kwargs)

        return run

    return wrapper


def init_mixnet_config(num_nodes: int) -> MixnetConfig:
    conn_degree = 4
    transmission_rate_per_sec = 3
    node_configs = [
        NodeConfig(X25519PrivateKey.generate(), conn_degree, transmission_rate_per_sec)
        for _ in range(num_nodes)
    ]
    membership = MixMembership(
        [NodePublicInfo(node_config.private_key) for node_config in node_configs]
    )
    return MixnetConfig(node_configs, membership)
