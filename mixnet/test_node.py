import asyncio
from datetime import datetime
from typing import Tuple
from unittest import IsolatedAsyncioTestCase

import numpy
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from pysphinx.sphinx import SphinxPacket

from mixnet.bls import generate_bls
from mixnet.mixnet import Mixnet, MixnetTopology
from mixnet.node import MixNode, NodeAddress, PacketPayloadQueue, PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec, poisson_mean_interval_sec
from mixnet.test_utils import with_test_timeout
from mixnet.utils import random_bytes


class TestMixNodeRunner(IsolatedAsyncioTestCase):
    @with_test_timeout(180)
    async def test_mixnode_runner_emission_rate(self):
        """
        Test if MixNodeRunner works as a M/M/inf queue.

        If inputs are arrived at Poisson rate `lambda`,
        and if processing is delayed according to an exponential distribution with a rate `mu`,
        the rate of outputs should be `lambda`.
        """
        mixnet, topology = self.init()
        inbound_socket: PacketQueue = asyncio.Queue()
        outbound_socket: PacketPayloadQueue = asyncio.Queue()

        packet, route = PacketBuilder.real(b"msg", mixnet, topology).next()

        delay_rate_per_min = 30  # mu (= 2s delay on average)
        # Start only the first mix node for testing
        runner, _ = await route[0].start(
            delay_rate_per_min, inbound_socket, outbound_socket
        )

        # Send packets to the first mix node in a Poisson distribution
        packet_count = 100
        emission_rate_per_min = 120  # lambda (= 2msg/sec)
        _ = asyncio.create_task(
            self.send_packets(
                inbound_socket,
                packet,
                route[0].addr,
                packet_count,
                emission_rate_per_min,
            )
        )

        # Calculate intervals between outputs and gather num_jobs in the first mix node.
        intervals = []
        num_jobs = []
        ts = datetime.now()
        for _ in range(packet_count):
            _ = await outbound_socket.get()
            now = datetime.now()
            intervals.append((now - ts).total_seconds())
            num_jobs.append(await runner.num_jobs())
            ts = now
        # Remove the first interval that would be much larger than other intervals,
        # because of the delay in mix node.
        intervals = intervals[1:]
        num_jobs = num_jobs[1:]

        # Check if the emission rate of the first mix node is the same as
        # the emission rate of the message sender, but with a delay.
        # If outputs follow the Poisson distribution with a rate `lambda`,
        # a mean interval between outputs must be `1/lambda`.
        self.assertAlmostEqual(
            float(numpy.mean(intervals)),
            poisson_mean_interval_sec(emission_rate_per_min),
            delta=1.0,
        )
        # If runner is a M/M/inf queue,
        # a mean number of jobs being processed/scheduled in the runner must be `lambda/mu`.
        self.assertAlmostEqual(
            float(numpy.mean(num_jobs)),
            round(emission_rate_per_min / delay_rate_per_min),
            delta=1.5,
        )

    @staticmethod
    async def send_packets(
        inbound_socket: PacketQueue,
        packet: SphinxPacket,
        node_addr: NodeAddress,
        cnt: int,
        rate_per_min: int,
    ):
        for _ in range(cnt):
            # Since the task is not heavy, just sleep for seconds instead of using emission_notifier
            await asyncio.sleep(poisson_interval_sec(rate_per_min))
            await inbound_socket.put((node_addr, packet))

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
