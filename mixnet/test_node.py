import asyncio
from datetime import datetime
from unittest import IsolatedAsyncioTestCase

import numpy
from pysphinx.sphinx import SphinxPacket

from mixnet.node import MixNode, NodeAddress, PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec, poisson_mean_interval_sec
from mixnet.test_utils import initial_topology, with_test_timeout


class TestMixNodeRunner(IsolatedAsyncioTestCase):
    @with_test_timeout(180)
    async def test_mixnode_emission_rate(self):
        """
        Test if MixNodeRunner works as a M/M/inf queue.

        If inputs are arrived at Poisson rate `lambda`,
        and if processing is delayed according to an exponential distribution with a rate `mu`,
        the rate of outputs should be `lambda`.
        """
        topology = initial_topology()

        packet, route = PacketBuilder.real(b"msg", topology).next()

        delay_rate_per_min = 30  # mu (= 2s delay on average)
        # Start only the first mix node for testing
        mixnode = await MixNode.new(
            topology, route[0].encryption_private_key, delay_rate_per_min
        )
        try:
            # Send packets to the first mix node in a Poisson distribution
            packet_count = 100
            emission_rate_per_min = 120  # lambda (= 2msg/sec)
            # This queue is just for counting how many packets have been sent so far.
            sent_packet_queue: PacketQueue = asyncio.Queue()
            sender_task = asyncio.create_task(
                self.send_packets(
                    mixnode.inbound_socket,
                    packet,
                    route[0].addr,
                    packet_count,
                    emission_rate_per_min,
                    sent_packet_queue,
                )
            )
            try:
                # Calculate intervals between outputs and gather num_jobs in the first mix node.
                intervals = []
                num_jobs = []
                ts = datetime.now()
                for _ in range(packet_count):
                    _ = await mixnode.outbound_socket.get()
                    now = datetime.now()
                    intervals.append((now - ts).total_seconds())

                    # Calculate the current # of jobs staying in the mix node
                    num_packets_emitted_from_mixnode = len(intervals)
                    num_packets_sent_to_mixnode = sent_packet_queue.qsize()
                    num_jobs.append(
                        num_packets_sent_to_mixnode - num_packets_emitted_from_mixnode
                    )

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
            finally:
                await sender_task
        finally:
            await mixnode.cancel()

    @staticmethod
    async def send_packets(
        inbound_socket: PacketQueue,
        packet: SphinxPacket,
        node_addr: NodeAddress,
        cnt: int,
        rate_per_min: int,
        # For testing purpose, to inform the caller how many packets have been sent to the inbound_socket
        sent_packet_queue: PacketQueue,
    ):
        for _ in range(cnt):
            # Since the task is not heavy, just sleep for seconds instead of using emission_notifier
            await asyncio.sleep(poisson_interval_sec(rate_per_min))
            await inbound_socket.put((node_addr, packet))
            await sent_packet_queue.put((node_addr, packet))
