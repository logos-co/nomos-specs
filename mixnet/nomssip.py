import asyncio
import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Awaitable, Callable

from mixnet.connection import DuplexConnection, MixSimplexConnection, SimplexConnection


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
        config: Config,
        handler: Callable[[bytes], Awaitable[None]],
    ):
        self.config = config
        self.conns: list[DuplexConnection] = []
        # A handler to process inbound messages.
        self.handler = handler
        self.packet_cache: set[bytes] = set()
        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks: set[asyncio.Task] = set()

    def add_conn(self, inbound: SimplexConnection, outbound: SimplexConnection):
        if len(self.conns) >= self.config.peering_degree:
            # For simplicity of the spec, reject the connection if the peering degree is reached.
            raise ValueError("The peering degree is reached.")

        noise_packet = self.__build_packet(
            self.PacketType.NOISE, bytes(self.config.msg_size)
        )
        conn = DuplexConnection(
            inbound,
            MixSimplexConnection(
                outbound,
                self.config.transmission_rate_per_sec,
                noise_packet,
            ),
        )

        self.conns.append(conn)
        task = asyncio.create_task(self.__process_inbound_conn(conn))
        self.tasks.add(task)
        # To discard the task from the set automatically when it is done.
        task.add_done_callback(self.tasks.discard)

    async def __process_inbound_conn(self, conn: DuplexConnection):
        while True:
            packet = await conn.recv()
            if self.__check_update_cache(packet):
                continue

            flag, msg = self.__parse_packet(packet)
            match flag:
                case self.PacketType.NOISE:
                    # Drop noise packet
                    continue
                case self.PacketType.REAL:
                    await self.__gossip(packet)
                    await self.handler(msg)

    async def gossip(self, msg: bytes):
        """
        Gossip a message to all connected peers with prepending a message flag
        """
        # The message size must be fixed.
        assert len(msg) == self.config.msg_size

        packet = self.__build_packet(self.PacketType.REAL, msg)
        await self.__gossip(packet)

    async def __gossip(self, packet: bytes):
        """
        An internal method to send a flagged packet to all connected peers
        """
        for conn in self.conns:
            await conn.send(packet)

    def __check_update_cache(self, packet: bytes) -> bool:
        """
        Add a message to the cache, and return True if the message was already in the cache.
        """
        hash = hashlib.sha256(packet).digest()
        if hash in self.packet_cache:
            return True
        self.packet_cache.add(hash)
        return False

    class PacketType(Enum):
        REAL = b"\x00"
        NOISE = b"\x01"

    @staticmethod
    def __build_packet(flag: PacketType, data: bytes) -> bytes:
        """
        Prepend a flag to the message, right before sending it via network channel.
        """
        return flag.value + data

    @staticmethod
    def __parse_packet(data: bytes) -> tuple[PacketType, bytes]:
        """
        Parse the message and extract the flag.
        """
        if len(data) < 1:
            raise ValueError("Invalid message format")
        return (Nomssip.PacketType(data[:1]), data[1:])
