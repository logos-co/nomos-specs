import asyncio

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.config import MixnetConfig, MixNodeInfo
from mixnet.robustness import MixnetTopologySize, Robustness, RobustnessMixnetConfig
from mixnet.utils import random_bytes


def with_test_timeout(t):
    def wrapper(coroutine):
        async def run(*args, **kwargs):
            async with asyncio.timeout(t):
                return await coroutine(*args, **kwargs)

        return run

    return wrapper


def init_robustness_mixnet_config() -> RobustnessMixnetConfig:
    mixnode_candidates = [
        MixNodeInfo(
            generate_bls(),
            X25519PrivateKey.generate(),
            random_bytes(32),
        )
        for _ in range(12)
    ]
    topology_size = MixnetTopologySize(3, 3)
    mixnet_layer_config = MixnetConfig(
        30,
        3,
        30,
        Robustness.build_topology(mixnode_candidates, topology_size, b"entropy"),
    )
    return RobustnessMixnetConfig(
        mixnode_candidates, topology_size, mixnet_layer_config
    )
