import asyncio

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.config import (
    MixClientConfig,
    MixNodeConfig,
    MixnetConfig,
    MixNodeInfo,
    MixnetTopology,
    MixnetTopologyConfig,
    MixnetTopologySize,
)
from mixnet.utils import random_bytes


def with_test_timeout(t):
    def wrapper(coroutine):
        async def run(*args, **kwargs):
            async with asyncio.timeout(t):
                return await coroutine(*args, **kwargs)

        return run

    return wrapper


def init_mixnet_config() -> MixnetConfig:
    topology_config = MixnetTopologyConfig(
        [
            MixNodeInfo(
                generate_bls(),
                X25519PrivateKey.generate(),
                random_bytes(32),
            )
            for _ in range(12)
        ],
        MixnetTopologySize(3, 3),
        b"entropy",
    )
    mixclient_config = MixClientConfig(30, 3, MixnetTopology(topology_config))
    mixnode_config = MixNodeConfig(
        topology_config.mixnode_candidates[0].encryption_private_key, 30
    )
    return MixnetConfig(topology_config, mixclient_config, mixnode_config)
