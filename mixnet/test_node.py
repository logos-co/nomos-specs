import queue
import threading
import time
from datetime import datetime

import numpy
import timeout_decorator
from pysphinx.sphinx import SphinxPacket

from mixnet.node import NodeAddress, PacketPayloadQueue, PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec, poisson_mean_interval_sec
from mixnet.test_mixnet import MixnetTestCase


class TestMixNodeRunner(MixnetTestCase):
    @timeout_decorator.timeout(180)
    def test_mixnode_runner_emission_rate(self):
        """
        Test if MixNodeRunner works as a M/M/inf queue.

        If inputs are arrived at Poisson rate `lambda`,
        and if processing is delayed according to an exponential distribution with a rate `mu`,
        the rate of outputs should be `lambda`.
        """
        mixnet = self.init(12, 3, 3, 60)
        inbound_socket: PacketQueue = queue.Queue()
        outbound_socket: PacketPayloadQueue = queue.Queue()

        packet, route = PacketBuilder.real(b"msg", mixnet).next()

        delay_rate_per_min = 30  # mu (= 2s delay on average)
        # Start only the first mix node for testing
        runner = route[0].start(delay_rate_per_min, inbound_socket, outbound_socket)

        # Send packets to the first mix node in a Poisson distribution
        packet_count = 100
        emission_rate_per_min = 120  # lambda (= 2msg/sec)
        sender = threading.Thread(
            target=self.send_packets,
            args=(
                inbound_socket,
                packet,
                route[0].addr,
                packet_count,
                emission_rate_per_min,
            ),
        )
        sender.daemon = True
        sender.start()

        # Calculate intervals between outputs and gather num_jobs in the first mix node.
        intervals = []
        num_jobs = []
        ts = datetime.now()
        for _ in range(packet_count):
            _ = outbound_socket.get()
            now = datetime.now()
            intervals.append((now - ts).total_seconds())
            num_jobs.append(runner.num_jobs())
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
            delta=1.0,
        )

    @staticmethod
    def send_packets(
        inbound_socket: PacketQueue,
        packet: SphinxPacket,
        node_addr: NodeAddress,
        cnt: int,
        rate_per_min: int,
    ):
        for _ in range(cnt):
            time.sleep(poisson_interval_sec(rate_per_min))
            inbound_socket.put((node_addr, packet))
