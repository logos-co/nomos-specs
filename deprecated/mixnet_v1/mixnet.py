from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Self, TypeAlias

from .client import MixClient
from .config import (
    MixnetConfig,
    MixnetTopology,
    MixnetTopologyConfig,
)
from .node import MixNode

EntropyQueue: TypeAlias = "asyncio.Queue[bytes]"


class Mixnet:
    topology_config: MixnetTopologyConfig

    mixclient: MixClient
    mixnode: MixNode
    entropy_queue: EntropyQueue
    task: asyncio.Task  # A reference just to prevent task from being garbage collected

    @classmethod
    async def new(
        cls,
        config: MixnetConfig,
        entropy_queue: EntropyQueue,
    ) -> Self:
        self = cls()
        self.topology_config = config.topology_config
        self.mixclient = await MixClient.new(config.mixclient_config)
        self.mixnode = await MixNode.new(config.mixnode_config)
        self.entropy_queue = entropy_queue
        self.task = asyncio.create_task(self.__consume_entropy())
        return self

    async def publish_message(self, msg: bytes) -> None:
        await self.mixclient.send_message(msg)

    def subscribe_messages(self) -> "asyncio.Queue[bytes]":
        return self.mixclient.subscribe_messages()

    async def __consume_entropy(
        self,
    ) -> None:
        while True:
            entropy = await self.entropy_queue.get()
            self.topology_config.entropy = entropy

            topology = MixnetTopology(self.topology_config)
            self.mixclient.set_topology(topology)

    async def cancel(self) -> None:
        self.task.cancel()
        with suppress(asyncio.CancelledError):
            await self.task

        await self.mixclient.cancel()
        await self.mixnode.cancel()

    # Only for testing
    def get_topology(self) -> MixnetTopology:
        return self.mixclient.get_topology()
