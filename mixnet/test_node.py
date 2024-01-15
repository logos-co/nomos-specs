import queue
import threading
import time
from datetime import datetime
from typing import Tuple
from unittest import TestCase

import numpy
import timeout_decorator
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from pysphinx.sphinx import SphinxPacket

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixnetTopology
from mixnet.node import InboundSocket, MixNode, OutboundSocket
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec, poisson_mean_interval_sec
from mixnet.utils import random_bytes


class TestMixNodeRunner(TestCase):
    @timeout_decorator.timeout(180)
    def test_mixnode_runner_emission_rate(self):
        mixnet, topology = self.init()
        inbound_socket: InboundSocket = queue.Queue()
        outbound_socket: OutboundSocket = queue.Queue()

        packet, route = PacketBuilder.real(b"msg", mixnet, topology).next()

        delay_rate_per_min = 6  # 10s delay on average
        # Start only the first mix node for testing
        route[0].start(delay_rate_per_min, inbound_socket, outbound_socket)

        # Send packets to the first mix node in a Poisson distribution
        packet_count = 50
        emission_rate_per_min = 60  # 1 msg/sec
        thread = threading.Thread(
            target=self.send_packets,
            args=(inbound_socket, packet, packet_count, emission_rate_per_min),
        )
        thread.daemon = True
        thread.start()

        # Check if the emission rate of the first mix node is the same as
        # the emission rate of the message sender, but with a delay.
        intervals = []
        ts = datetime.now()
        for _ in range(packet_count):
            _ = outbound_socket.get()
            now = datetime.now()
            intervals.append((now - ts).total_seconds())
            ts = now
        # Remove the first interval that would be much larger than other intervals,
        # because of the 10s delay on average.
        intervals = intervals[1:]

        self.assertEqual(
            numpy.mean(intervals).round(),
            poisson_mean_interval_sec(emission_rate_per_min),
        )

    @staticmethod
    def send_packets(
        inbound_socket: InboundSocket,
        packet: SphinxPacket,
        cnt: int,
        rate_per_min: int,
    ):
        for _ in range(cnt):
            time.sleep(poisson_interval_sec(rate_per_min))
            inbound_socket.put(packet)

    @staticmethod
    def init() -> Tuple[Mixnet, MixnetTopology]:
        mixnet = Mixnet(
            [
                MixNode(
                    generate_bls(),
                    X25519PrivateKey.generate(),
                    random_bytes(32),
                )
                for _ in range(12)
            ]
        )
        topology = mixnet.build_topology(b"entropy", 3, 3)
        return mixnet, topology
