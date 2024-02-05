from __future__ import annotations

import asyncio
from typing import Self

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
)

from mixnet.client import MixClient
from mixnet.config import MixnetConfig
from mixnet.node import MixNode


class Mixnet:
    __mixclient: MixClient
    __mixnode: MixNode

    @classmethod
    async def new(
        cls,
        encryption_private_key: X25519PrivateKey,
        config: MixnetConfig,
    ) -> Self:
        self = cls()
        self.__mixclient = await MixClient.new(config)
        self.__mixnode = await MixNode.new(encryption_private_key, config)
        return self

    async def publish_message(self, msg: bytes) -> None:
        await self.__mixclient.send_message(msg)

    def subscribe_messages(self) -> "asyncio.Queue[bytes]":
        return self.__mixclient.subscribe_messages()

    def set_config(self, config: MixnetConfig) -> None:
        """
        Replace the old config with the new config received.

        In real implementations, this method should be a long-running task, accepting configs periodically.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__mixclient.set_config(config)
        self.__mixnode.set_config(config)

    def get_config(self) -> MixnetConfig:
        return self.__mixclient.get_config()

    async def cancel(self) -> None:
        await self.__mixclient.cancel()
        await self.__mixnode.cancel()
