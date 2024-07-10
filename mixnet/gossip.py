import asyncio
import hashlib
from typing import Awaitable, Callable

from mixnet.config import GossipConfig
from mixnet.connection import DuplexConnection


class GossipChannel:
    config: GossipConfig
    conns: list[DuplexConnection]
    handler: Callable[[bytes], Awaitable[bytes | None]]
    msg_cache: set[bytes]

    def __init__(
        self,
        config: GossipConfig,
        handler: Callable[[bytes], Awaitable[bytes | None]],
    ):
        self.config = config
        self.conns = []
        self.handler = handler
        self.msg_cache = set()
        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks = set()

    def add_conn(self, conn: DuplexConnection):
        if len(self.conns) >= self.config.peering_degree:
            # For simplicity of the spec, reject the connection if the peering degree is reached.
            raise ValueError("The peering degree is reached.")

        self.conns.append(conn)
        task = asyncio.create_task(self.__process_inbound_conn(conn))
        self.tasks.add(task)
        # To discard the task from the set automatically when it is done.
        task.add_done_callback(self.tasks.discard)

    async def __process_inbound_conn(self, conn: DuplexConnection):
        while True:
            msg = await conn.recv()
            # Don't process the same message twice.
            msg_hash = hashlib.sha256(msg).digest()
            if msg_hash in self.msg_cache:
                continue
            self.msg_cache.add(msg_hash)

            new_msg = await self.handler(msg)
            if new_msg is not None:
                await self.gossip(new_msg)

    async def gossip(self, packet: bytes):
        for conn in self.conns:
            await conn.send(packet)
