import math
from collections import Counter
from typing import Awaitable

import pandas

from mixnet.connection import SimplexConnection
from mixnet.framework import Framework, Queue
from mixnet.sim.config import NetworkConfig
from mixnet.sim.state import NodeState


class MeteredRemoteSimplexConnection(SimplexConnection):
    """
    A simplex connection implementation that simulates network latency and measures bandwidth usages.
    """

    def __init__(
        self,
        config: NetworkConfig,
        framework: Framework,
        send_node_states: list[NodeState],
        recv_node_states: list[NodeState],
    ):
        self.framework = framework
        # A connection has a random constant latency
        self.latency = config.latency.random_latency()
        # A queue where a sender puts messages to be sent
        self.send_queue = framework.queue()
        # A queue that connects send_queue and recv_queue (to measure bandwidths and simulate latency)
        self.mid_queue = framework.queue()
        # A queue where a receiver gets messages
        self.recv_queue = framework.queue()
        # A task that reads messages from send_queue, updates bandwidth stats, and puts them to mid_queue
        self.send_meters: list[int] = []
        self.send_task = framework.spawn(self.__run_send_task())
        # A task that reads messages from mid_queue, simulates network latency, updates bandwidth stats, and puts them to recv_queue
        self.recv_meters: list[int] = []
        self.recv_task = framework.spawn(self.__run_recv_task())
        # To measure node states over time
        self.send_node_states = send_node_states
        self.recv_node_states = recv_node_states
        # To measure the size of messages sent via this connection
        self.msg_sizes: Counter[int] = Counter()

    async def send(self, data: bytes) -> None:
        await self.send_queue.put(data)
        self.msg_sizes.update([len(data)])
        # The time unit of node states is milliseconds
        ms = math.floor(self.framework.now() * 1000)
        self.send_node_states[ms] = NodeState.SENDING

    async def recv(self) -> bytes:
        data = await self.recv_queue.get()
        # The time unit of node states is milliseconds
        ms = math.floor(self.framework.now() * 1000)
        self.send_node_states[ms] = NodeState.RECEIVING
        return data

    async def __run_send_task(self):
        """
        A task that reads messages from send_queue, updates bandwidth stats, and puts them to mid_queue
        """
        start_time = self.framework.now()
        while True:
            data = await self.send_queue.get()
            self.__update_meter(self.send_meters, len(data), start_time)
            await self.mid_queue.put(data)

    async def __run_recv_task(self):
        """
        A task that reads messages from mid_queue, simulates network latency, updates bandwidth stats, and puts them to recv_queue
        """
        start_time = self.framework.now()
        while True:
            data = await self.mid_queue.get()
            if data is None:
                break
            await self.framework.sleep(self.latency)
            self.__update_meter(self.recv_meters, len(data), start_time)
            await self.recv_queue.put(data)

    def __update_meter(self, meters: list[int], size: int, start_time: float):
        """
        Accumulates the bandwidth usage in the current time slot (seconds).
        """
        slot = math.floor(self.framework.now() - start_time)
        assert slot >= len(meters) - 1
        # Fill zeros for the empty time slots
        meters.extend([0] * (slot - len(meters) + 1))
        meters[-1] += size

    def sending_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.send_meters)

    def receiving_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.recv_meters)

    def __bandwidths(self, meters: list[int]) -> pandas.Series:
        return pandas.Series(meters, name="bandwidth")
