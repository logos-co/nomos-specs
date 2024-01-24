from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Tuple, TypeAlias

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from pysphinx.node import Node
from pysphinx.sphinx import (
    Payload,
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
    UnknownHeaderTypeError,
)

from mixnet.bls import BlsPrivateKey, BlsPublicKey
from mixnet.poisson import poisson_interval_sec

NodeId: TypeAlias = BlsPublicKey
# 32-byte that represents an IP address and a port of a mix node.
NodeAddress: TypeAlias = bytes

PacketQueue: TypeAlias = "asyncio.Queue[Tuple[NodeAddress, SphinxPacket]]"
PacketPayloadQueue: TypeAlias = (
    "asyncio.Queue[Tuple[NodeAddress, SphinxPacket | Payload]]"
)


@dataclass
class MixNode:
    identity_private_key: BlsPrivateKey
    encryption_private_key: X25519PrivateKey
    addr: NodeAddress

    def identity_public_key(self) -> BlsPublicKey:
        return self.identity_private_key.get_g1()

    def encryption_public_key(self) -> X25519PublicKey:
        return self.encryption_private_key.public_key()

    def sphinx_node(self) -> Node:
        return Node(self.encryption_private_key, self.addr)

    def start(
        self,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
        inbound_socket: PacketQueue,
        outbound_socket: PacketPayloadQueue,
    ) -> Tuple[MixNodeRunner, asyncio.Task]:
        runner = MixNodeRunner(
            self.encryption_private_key,
            delay_rate_per_min,
            inbound_socket,
            outbound_socket,
        )
        task = asyncio.create_task(runner.run())
        return runner, task


class MixNodeRunner:
    """
    A class handling incoming packets with delays

    This class is defined separated with the MixNode class,
    in order to define the MixNode as a simple dataclass for clarity.
    """

    def __init__(
        self,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
        inbound_socket: PacketQueue,
        outbound_socket: PacketPayloadQueue,
    ):
        self.encryption_private_key = encryption_private_key
        self.delay_rate_per_min = delay_rate_per_min
        self.inbound_socket = inbound_socket
        self.outbound_socket = outbound_socket
        self.packet_processing_tasks = set()

    async def run(self):
        """
        Read SphinxPackets from inbound socket and spawn a thread for each packet to process it.

        This thread approximates a M/M/inf queue.
        """
        while True:
            _, packet = await self.inbound_socket.get()
            task = asyncio.create_task(
                self.process_packet(
                    packet,
                )
            )
            self.packet_processing_tasks.add(task)
            task.add_done_callback(self.packet_processing_tasks.discard)

    async def process_packet(
        self,
        packet: SphinxPacket,
    ):
        """
        Process a single packet with a delay that follows exponential distribution,
        and forward it to the next mix node or the mix destination

        This thread is a single server (worker) in a M/M/inf queue that MixNodeRunner approximates.
        """
        delay_sec = poisson_interval_sec(self.delay_rate_per_min)
        await asyncio.sleep(delay_sec)

        processed = packet.process(self.encryption_private_key)
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

    async def num_jobs(self) -> int:
        """
        Return the number of packets that are being processed or still in the inbound socket.

        If this thread works as a M/M/inf queue completely,
        the number of packets that are still in the inbound socket must be always 0.
        """
        return self.inbound_socket.qsize() + len(self.packet_processing_tasks)
