import asyncio
from typing import List, Tuple

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.robustness import Robustness
from mixnet.topology import MixnetTopology, MixnetTopologySize, MixNodeInfo
from mixnet.utils import random_bytes


def with_test_timeout(t):
    def wrapper(coroutine):
        async def run(*args, **kwargs):
            async with asyncio.timeout(t):
                return await coroutine(*args, **kwargs)

        return run

    return wrapper


def init() -> Tuple[List[MixNodeInfo], MixnetTopologySize]:
    mixnode_candidates = [
        MixNodeInfo(
            generate_bls(),
            X25519PrivateKey.generate(),
            random_bytes(32),
        )
        for _ in range(12)
    ]
    topology_size = MixnetTopologySize(3, 3)
    return (mixnode_candidates, topology_size)


def initial_topology() -> MixnetTopology:
    mixnode_candidates, topology_size = init()
    return Robustness.build_topology(mixnode_candidates, topology_size, b"entropy")
