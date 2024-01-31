from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Self, TypeAlias

from mixnet.client import MixClient
from mixnet.config import MixnetConfig, MixnetTopology, MixnetTopologyConfig
from mixnet.node import MixNode

EntropyQueue: TypeAlias = "asyncio.Queue[bytes]"


class Mixnet:
    __topology_config: MixnetTopologyConfig

    __mixclient: MixClient
    __mixnode: MixNode
    __entropy_queue: EntropyQueue
    __task: asyncio.Task  # A reference just to prevent task from being garbage collected

    @classmethod
    async def new(
        cls,
        config: MixnetConfig,
        entropy_queue: EntropyQueue,
    ) -> Self:
        self = cls()
        self.__topology_config = config.topology_config
        self.__mixclient = await MixClient.new(config.mixclient_config)
        self.__mixnode = await MixNode.new(config.mixnode_config)
        self.__entropy_queue = entropy_queue
        self.__task = asyncio.create_task(self.__consume_entropy())
        return self

    async def publish_message(self, msg: bytes) -> None:
        await self.__mixclient.send_message(msg)

    def subscribe_messages(self) -> "asyncio.Queue[bytes]":
        return self.__mixclient.subscribe_messages()

    async def __consume_entropy(
        self,
    ) -> None:
        while True:
            entropy = await self.__entropy_queue.get()
            self.__topology_config.entropy = entropy

            topology = MixnetTopology(self.__topology_config)
            self.__mixclient.set_topology(topology)

    async def cancel(self) -> None:
        self.__task.cancel()
        with suppress(asyncio.CancelledError):
            await self.__task

        await self.__mixclient.cancel()
        await self.__mixnode.cancel()

    # Only for testing
    def get_topology(self) -> MixnetTopology:
        return self.__mixclient.get_topology()
