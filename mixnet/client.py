from __future__ import annotations

import queue
import time
from datetime import datetime, timedelta
from threading import Thread

from mixnet.mixnet import Mixnet, MixnetTopology
from mixnet.node import PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec


class MixClientRunner(Thread):
    """
    Emit packets at the Poisson emission_rate_per_min.

    If a real packet is scheduled to be sent, this thread sends the real packet to the mixnet,
    and schedules redundant real packets to be emitted in the next turns.

    If no real packet is not scheduled, this thread emits a cover packet according to the emission_rate_per_min.
    """

    def __init__(
        self,
        mixnet: Mixnet,
        topology: MixnetTopology,
        emission_rate_per_min: int,  # Poisson rate parameter: lambda in the spec
        redundancy: int,  # b in the spec
        real_packet_queue: PacketQueue,
        outbound_socket: PacketQueue,
    ):
        super().__init__()
        self.mixnet = mixnet
        self.topology = topology
        self.emission_rate_per_min = emission_rate_per_min
        self.redundancy = redundancy
        self.real_packet_queue = real_packet_queue
        self.redundant_real_packet_queue: PacketQueue = queue.Queue()
        self.outbound_socket = outbound_socket

    def run(self) -> None:
        # Here in Python, this thread is implemented in synchronous manner.
        # In the real implementation, consider implementing this in asynchronous if possible.

        next_emission_ts = datetime.now() + timedelta(
            seconds=poisson_interval_sec(self.emission_rate_per_min)
        )

        while True:
            time.sleep(1 / 1000)

            if datetime.now() < next_emission_ts:
                continue

            next_emission_ts += timedelta(
                seconds=poisson_interval_sec(self.emission_rate_per_min)
            )

            if not self.redundant_real_packet_queue.empty():
                addr, packet = self.redundant_real_packet_queue.get()
                self.outbound_socket.put((addr, packet))
                continue

            if not self.real_packet_queue.empty():
                addr, packet = self.real_packet_queue.get()
                # Schedule redundant real packets
                for _ in range(self.redundancy - 1):
                    self.redundant_real_packet_queue.put((addr, packet))
                self.outbound_socket.put((addr, packet))

            packet, route = PacketBuilder.drop_cover(b"drop cover", self.mixnet).next()
            self.outbound_socket.put((route[0].addr, packet))
