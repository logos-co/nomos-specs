import math
from collections import Counter
from typing import Awaitable

import pandas

from mixnet.connection import SimplexConnection
from mixnet.framework.framework import Framework, Queue
from mixnet.sim.config import NetworkConfig
from mixnet.sim.state import NodeState


class MeteredRemoteSimplexConnection(SimplexConnection):
    framework: Framework
    latency: float
    send_queue: Queue
    mid_queue: Queue
    recv_queue: Queue
    send_task: Awaitable
    send_meters: list[int]
    recv_task: Awaitable
    recv_meters: list[int]
    send_node_states: list[NodeState]
    recv_node_states: list[NodeState]
    msg_sizes: Counter[int]

    def __init__(
        self,
        config: NetworkConfig,
        framework: Framework,
        send_node_states: list[NodeState],
        recv_node_states: list[NodeState],
    ):
        self.framework = framework
        self.latency = config.random_latency()
        self.send_queue = framework.queue()
        self.mid_queue = framework.queue()
        self.recv_queue = framework.queue()
        self.send_meters = []
        self.send_task = framework.spawn(self.__run_send_task())
        self.recv_meters = []
        self.recv_task = framework.spawn(self.__run_recv_task())
        self.send_node_states = send_node_states
        self.recv_node_states = recv_node_states
        self.msg_sizes = Counter()

    async def send(self, data: bytes) -> None:
        await self.send_queue.put(data)
        self.msg_sizes.update([len(data)])
        ms = math.floor(self.framework.now() * 1000)
        self.send_node_states[ms] = NodeState.SENDING

    async def recv(self) -> bytes:
        data = await self.recv_queue.get()
        ms = math.floor(self.framework.now() * 1000)
        self.send_node_states[ms] = NodeState.RECEIVING
        return data

    async def __run_send_task(self):
        start_time = self.framework.now()
        while True:
            data = await self.send_queue.get()
            self.__update_meter(self.send_meters, len(data), start_time)
            await self.mid_queue.put(data)

    async def __run_recv_task(self):
        start_time = self.framework.now()
        while True:
            data = await self.mid_queue.get()
            if data is None:
                break
            await self.framework.sleep(self.latency)
            self.__update_meter(self.recv_meters, len(data), start_time)
            await self.recv_queue.put(data)

    def __update_meter(self, meters: list[int], size: int, start_time: float):
        slot = math.floor(self.framework.now() - start_time)
        assert slot >= len(meters) - 1
        meters.extend([0] * (slot - len(meters) + 1))
        meters[-1] += size

    def sending_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.send_meters)

    def receiving_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.recv_meters)

    def __bandwidths(self, meters: list[int]) -> pandas.Series:
        return pandas.Series(meters, name="bandwidth")
