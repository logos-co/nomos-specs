from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable, Self

from mixnet.connection import DuplexConnection, MixSimplexConnection, SimplexConnection
from mixnet.error import PeeringDegreeReached
from mixnet.framework import Framework


class Nomssip:
    """
    A NomMix gossip channel that broadcasts messages to all connected peers.
    Peers are connected via DuplexConnection.
    """

    @dataclass
    class Config:
        transmission_rate_per_sec: int
        peering_degree: int
        msg_size: int

    def __init__(
        self,
        framework: Framework,
        config: Config,
        handler: Callable[[bytes], Awaitable[None]],
    ):
        self.framework = framework
        self.config = config
        self.conns: list[DuplexConnection] = []
        # A handler to process inbound messages.
        self.handler = handler
        self.packet_cache: set[bytes] = set()
        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks: set[Awaitable] = set()

    def can_accept_conn(self) -> bool:
        return len(self.conns) < self.config.peering_degree

    def add_conn(self, inbound: SimplexConnection, outbound: SimplexConnection):
        if not self.can_accept_conn():
            # For simplicity of the spec, reject the connection if the peering degree is reached.
            raise PeeringDegreeReached()

        noise_packet = FlaggedPacket(
            FlaggedPacket.Flag.NOISE, bytes(self.config.msg_size)
        ).bytes()
        conn = DuplexConnection(
            inbound,
            MixSimplexConnection(
                self.framework,
                outbound,
                self.config.transmission_rate_per_sec,
                noise_packet,
            ),
        )

        self.conns.append(conn)
        task = self.framework.spawn(self.__process_inbound_conn(conn))
        self.tasks.add(task)

    async def __process_inbound_conn(self, conn: DuplexConnection):
        while True:
            packet = await conn.recv()
            if self.__check_update_cache(packet):
                continue

            packet = FlaggedPacket.from_bytes(packet)
            match packet.flag:
                case FlaggedPacket.Flag.NOISE:
                    # Drop noise packet
                    continue
                case FlaggedPacket.Flag.REAL:
                    await self.__gossip_flagged_packet(packet)
                    await self.handler(packet.message)

    async def gossip(self, msg: bytes):
        """
        Gossip a message to all connected peers with prepending a message flag
        """
        # The message size must be fixed.
        assert len(msg) == self.config.msg_size

        packet = FlaggedPacket(FlaggedPacket.Flag.REAL, msg)
        await self.__gossip_flagged_packet(packet)

    async def __gossip_flagged_packet(self, packet: FlaggedPacket):
        """
        An internal method to send a flagged packet to all connected peers
        """
        for conn in self.conns:
            await conn.send(packet.bytes())

    def __check_update_cache(self, packet: bytes) -> bool:
        """
        Add a message to the cache, and return True if the message was already in the cache.
        """
        hash = hashlib.sha256(packet).digest()
        if hash in self.packet_cache:
            return True
        self.packet_cache.add(hash)
        return False


class FlaggedPacket:
    class Flag(Enum):
        REAL = b"\x00"
        NOISE = b"\x01"

    def __init__(self, flag: Flag, message: bytes):
        self.flag = flag
        self.message = message

    def bytes(self) -> bytes:
        return self.flag.value + self.message

    @classmethod
    def from_bytes(cls, packet: bytes) -> Self:
        """
        Parse a flagged packet from bytes
        """
        if len(packet) < 1:
            raise ValueError("Invalid message format")
        return cls(cls.Flag(packet[:1]), packet[1:])
