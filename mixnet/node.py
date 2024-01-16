from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from threading import Thread
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

PacketQueue: TypeAlias = "queue.Queue[Tuple[NodeAddress, SphinxPacket]]"
PacketPayloadQueue: TypeAlias = (
    "queue.Queue[Tuple[NodeAddress, SphinxPacket | Payload]]"
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
        delay_rate_per_min: int,
        inbound_socket: PacketQueue,
        outbound_socket: PacketPayloadQueue,
    ) -> MixNodeRunner:
        thread = MixNodeRunner(
            self.encryption_private_key,
            delay_rate_per_min,
            inbound_socket,
            outbound_socket,
        )
        thread.daemon = True
        thread.start()
        return thread


class MixNodeRunner(Thread):
    """
    Read SphinxPackets from inbound socket and spawn a thread for each packet to process it.

    This thread approximates a M/M/inf queue.
    """

    def __init__(
        self,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
        inbound_socket: PacketQueue,
        outbound_socket: PacketPayloadQueue,
    ):
        super().__init__()
        self.encryption_private_key = encryption_private_key
        self.delay_rate_per_min = delay_rate_per_min
        self.inbound_socket = inbound_socket
        self.outbound_socket = outbound_socket
        self.num_processing = AtomicInt(0)

    def run(self) -> None:
        # Here in Python, this thread is implemented in synchronous manner.
        # In the real implementation, consider implementing this in asynchronous if possible,
        # to approximate a M/M/inf queue
        while True:
            _, packet = self.inbound_socket.get()
            thread = MixNodePacketProcessor(
                packet,
                self.encryption_private_key,
                self.delay_rate_per_min,
                self.outbound_socket,
                self.num_processing,
            )
            thread.daemon = True
            self.num_processing.add(1)
            thread.start()

    def num_jobs(self) -> int:
        """
        Return the number of packets that are being processed or still in the inbound socket.

        If this thread works as a M/M/inf queue completely,
        the number of packets that are still in the inbound socket must be always 0.
        """
        return self.num_processing.get() + self.inbound_socket.qsize()


class MixNodePacketProcessor(Thread):
    """
    Process a single packet with a delay that follows exponential distribution,
    and forward it to the next mix node or the mix destination

    This thread is a single server (worker) in a M/M/inf queue that MixNodeRunner approximates.
    """

    def __init__(
        self,
        packet: SphinxPacket,
        encryption_private_key: X25519PrivateKey,
        delay_rate_per_min: int,  # Poisson rate parameter: mu
        outbound_socket: PacketPayloadQueue,
        num_processing: AtomicInt,
    ):
        super().__init__()
        self.packet = packet
        self.encryption_private_key = encryption_private_key
        self.delay_rate_per_min = delay_rate_per_min
        self.outbound_socket = outbound_socket
        self.num_processing = num_processing

    def run(self) -> None:
        delay_sec = poisson_interval_sec(self.delay_rate_per_min)
        time.sleep(delay_sec)

        processed = self.packet.process(self.encryption_private_key)
        match processed:
            case ProcessedForwardHopPacket():
                self.outbound_socket.put(
                    (processed.next_node_address, processed.next_packet)
                )
            case ProcessedFinalHopPacket():
                self.outbound_socket.put(
                    (processed.destination_node_address, processed.payload)
                )
            case _:
                raise UnknownHeaderTypeError

        self.num_processing.sub(1)


class AtomicInt:
    def __init__(self, initial: int) -> None:
        self.lock = threading.Lock()
        self.value = initial

    def add(self, v: int):
        with self.lock:
            self.value += v

    def sub(self, v: int):
        with self.lock:
            self.value -= v

    def get(self) -> int:
        with self.lock:
            return self.value
