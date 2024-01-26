from __future__ import annotations

import asyncio
from typing import Self

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
)

from mixnet.client import MixClient
from mixnet.node import MixNode
from mixnet.topology import MixnetTopology


class Mixnet:
    __mixclient: MixClient
    __mixnode: MixNode

    @classmethod
    async def new(
        cls,
        initial_topology: MixnetTopology,
        emission_rate_per_min: int,  # Poisson rate parameter: lambda
        redundancy: int,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
    ) -> Self:
        self = cls()
        self.__mixclient = await MixClient.new(
            initial_topology, emission_rate_per_min, redundancy
        )
        self.__mixnode = await MixNode.new(
            initial_topology, encryption_private_key, delay_rate_per_min
        )
        return self

    async def publish_message(self, msg: bytes) -> None:
        await self.__mixclient.send_message(msg)

    def subscribe_messages(self) -> "asyncio.Queue[bytes]":
        return self.__mixclient.subscribe_messages()

    def set_topology(self, topology: MixnetTopology) -> None:
        """
        Replace the old topology with the new topology received, and start establishing new network connections in background.

        In real implementations, this method should be a long-running task, accepting topologies periodically.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__mixclient.set_topology(topology)
        self.__mixnode.set_topology(topology)

    def get_topology(self) -> MixnetTopology:
        return self.__mixclient.topology

    async def cancel(self) -> None:
        await self.__mixclient.cancel()
        await self.__mixnode.cancel()
