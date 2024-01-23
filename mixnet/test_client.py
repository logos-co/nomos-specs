import queue
from datetime import datetime
from typing import Tuple
from unittest import TestCase

import numpy
import timeout_decorator
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from mixnet.bls import generate_bls
from mixnet.client import MixClientRunner
from mixnet.mixnet import Mixnet, MixnetTopology
from mixnet.node import MixNode, PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_mean_interval_sec
from mixnet.utils import random_bytes


class TestMixClientRunner(TestCase):
    @timeout_decorator.timeout(180)
    def test_mixclient_runner_emission_rate(self):
        mixnet, topology = self.init()
        real_packet_queue: PacketQueue = queue.Queue()
        outbound_socket: PacketQueue = queue.Queue()

        emission_rate_per_min = 30
        redundancy = 3
        client = MixClientRunner(
            mixnet,
            topology,
            emission_rate_per_min,
            redundancy,
            real_packet_queue,
            outbound_socket,
        )
        client.daemon = True
        client.start()

        # Create packets. At least two packets are expected to be generated from a 3500-byte msg
        builder = PacketBuilder.real(random_bytes(3500), mixnet, topology)
        # Schedule two packets to the mix client without any interval
        packet, route = builder.next()
        real_packet_queue.put((route[0].addr, packet))
        packet, route = builder.next()
        real_packet_queue.put((route[0].addr, packet))

        # Calculate intervals between packet emissions from the mix client
        intervals = []
        ts = datetime.now()
        for _ in range(30):
            _ = outbound_socket.get()
            now = datetime.now()
            intervals.append((now - ts).total_seconds())
            ts = now

        # Check if packets were emitted at the Poisson emission_rate
        # If emissions follow the Poisson distribution with a rate `lambda`,
        # a mean interval between emissions must be `1/lambda`.
        self.assertAlmostEqual(
            float(numpy.mean(intervals)),
            poisson_mean_interval_sec(emission_rate_per_min),
            delta=1.0,
        )

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
