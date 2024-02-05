import asyncio
from datetime import datetime

import numpy

from mixnet.client import mixclient_emitter
from mixnet.node import PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_mean_interval_sec
from mixnet.test_mixnet import TestMixnet
from mixnet.test_utils import with_test_timeout
from mixnet.utils import random_bytes


class TestMixClient(TestMixnet):
    @with_test_timeout(100)
    async def test_mixclient_emitter(self):
        mixnet, _ = self.init()
        real_packet_queue: PacketQueue = asyncio.Queue()
        outbound_socket: PacketQueue = asyncio.Queue()

        emission_rate_per_min = 30
        redundancy = 3
        _ = asyncio.create_task(
            mixclient_emitter(
                mixnet,
                emission_rate_per_min,
                redundancy,
                real_packet_queue,
                outbound_socket,
            )
        )

        # Create packets. At least two packets are expected to be generated from a 3500-byte msg
        builder = PacketBuilder.real(random_bytes(3500), mixnet)
        # Schedule two packets to the mix client without any interval
        packet, route = builder.next()
        await real_packet_queue.put((route[0].addr, packet))
        packet, route = builder.next()
        await real_packet_queue.put((route[0].addr, packet))

        # Calculate intervals between packet emissions from the mix client
        intervals = []
        ts = datetime.now()
        for _ in range(30):
            _ = await outbound_socket.get()
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
