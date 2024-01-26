from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Self, Tuple, TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
)
from pysphinx.sphinx import (
    Payload,
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
    UnknownHeaderTypeError,
)

from mixnet.poisson import poisson_interval_sec
from mixnet.topology import MixnetTopology, NodeAddress

PacketQueue: TypeAlias = "asyncio.Queue[Tuple[NodeAddress, SphinxPacket]]"
PacketPayloadQueue: TypeAlias = (
    "asyncio.Queue[Tuple[NodeAddress, SphinxPacket | Payload]]"
)


class MixNode:
    """
    A class handling incoming packets with delays

    This class is defined separated with the MixNode class,
    in order to define the MixNode as a simple dataclass for clarity.
    """

    __topology: MixnetTopology

    inbound_socket: PacketQueue
    outbound_socket: PacketPayloadQueue
    __task: asyncio.Task  # A reference just to prevent task from being garbage collected

    @classmethod
    async def new(
        cls,
        initial_topology: MixnetTopology,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
    ) -> Self:
        self = cls()
        self.set_topology(initial_topology)
        self.inbound_socket = asyncio.Queue()
        self.outbound_socket = asyncio.Queue()
        self.__task = asyncio.create_task(
            self.__run(encryption_private_key, delay_rate_per_min)
        )
        return self

    async def __run(
        self,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
    ):
        """
        Read SphinxPackets from inbound socket and spawn a thread for each packet to process it.

        This thread approximates a M/M/inf queue.
        """

        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks = set()

        while True:
            _, packet = await self.inbound_socket.get()
            task = asyncio.create_task(
                self.__process_packet(
                    packet, encryption_private_key, delay_rate_per_min
                )
            )
            self.tasks.add(task)
            # To discard the task from the set automatically when it is done.
            task.add_done_callback(self.tasks.discard)

    async def __process_packet(
        self,
        packet: SphinxPacket,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
    ):
        """
        Process a single packet with a delay that follows exponential distribution,
        and forward it to the next mix node or the mix destination

        This thread is a single server (worker) in a M/M/inf queue that MixNodeRunner approximates.
        """
        delay_sec = poisson_interval_sec(delay_rate_per_min)
        await asyncio.sleep(delay_sec)

        processed = packet.process(encryption_private_key)
        match processed:
            case ProcessedForwardHopPacket():
                await self.outbound_socket.put(
                    (processed.next_node_address, processed.next_packet)
                )
            case ProcessedFinalHopPacket():
                await self.outbound_socket.put(
                    (processed.destination_node_address, processed.payload)
                )
            case _:
                raise UnknownHeaderTypeError

    def set_topology(self, topology: MixnetTopology) -> None:
        """
        Replace the old topology with the new topology received, and start establishing new network connections in background.

        In real implementations, this method may be integrated in a long-running task.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__topology = topology
        self.__establish_connections()

    def __establish_connections(self) -> None:
        """
        Establish network connections in advance based on the topology received.

        This is just a preparation to forward subsequent packets as quickly as possible,
        but this is not a strict requirement.

        In real implementations, this should be a background task.
        """
        pass

    async def cancel(self) -> None:
        self.__task.cancel()
        with suppress(asyncio.CancelledError):
            await self.__task
