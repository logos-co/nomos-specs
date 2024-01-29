from datetime import datetime
from unittest import IsolatedAsyncioTestCase

import numpy

from mixnet.client import MixClient
from mixnet.poisson import poisson_mean_interval_sec
from mixnet.test_utils import (
    init_robustness_mixnet_config,
    with_test_timeout,
)
from mixnet.utils import random_bytes


class TestMixClient(IsolatedAsyncioTestCase):
    @with_test_timeout(100)
    async def test_mixclient(self):
        config = init_robustness_mixnet_config().mixnet_layer_config
        config.emission_rate_per_min = 30
        config.redundancy = 3

        mixclient = await MixClient.new(config)
        try:
            # Send a 3500-byte msg, expecting that it is split into at least two packets
            await mixclient.send_message(random_bytes(3500))

            # Calculate intervals between packet emissions from the mix client
            intervals = []
            ts = datetime.now()
            for _ in range(30):
                _ = await mixclient.outbound_socket.get()
                now = datetime.now()
                intervals.append((now - ts).total_seconds())
                ts = now

            # Check if packets were emitted at the Poisson emission_rate
            # If emissions follow the Poisson distribution with a rate `lambda`,
            # a mean interval between emissions must be `1/lambda`.
            self.assertAlmostEqual(
                float(numpy.mean(intervals)),
                poisson_mean_interval_sec(config.emission_rate_per_min),
                delta=1.0,
            )
        finally:
            await mixclient.cancel()
