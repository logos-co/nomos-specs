import math
from typing import Awaitable

import pandas

from mixnet.connection import SimplexConnection
from mixnet.framework.framework import Framework, Queue
from mixnet.sim.config import NetworkConfig


class MeteredRemoteSimplexConnection(SimplexConnection):
    framework: Framework
    latency: float
    outputs: Queue
    conn: Queue
    inputs: Queue
    output_task: Awaitable
    output_meters: list[int]
    input_task: Awaitable
    input_meters: list[int]

    def __init__(self, config: NetworkConfig, framework: Framework):
        self.framework = framework
        self.latency = config.seed.random() * config.max_latency_sec
        self.outputs = framework.queue()
        self.conn = framework.queue()
        self.inputs = framework.queue()
        self.output_meters = []
        self.output_task = framework.spawn(self.__run_output_task())
        self.input_meters = []
        self.input_task = framework.spawn(self.__run_input_task())

    async def send(self, data: bytes) -> None:
        await self.outputs.put(data)

    async def recv(self) -> bytes:
        return await self.inputs.get()

    async def __run_output_task(self):
        start_time = self.framework.now()
        while True:
            data = await self.outputs.get()
            self.__update_meter(self.output_meters, len(data), start_time)
            await self.conn.put(data)

    async def __run_input_task(self):
        start_time = self.framework.now()
        while True:
            data = await self.conn.get()
            if data is None:
                break
            await self.framework.sleep(self.latency)
            self.__update_meter(self.input_meters, len(data), start_time)
            await self.inputs.put(data)

    def __update_meter(self, meters: list[int], size: int, start_time: float):
        slot = math.floor(self.framework.now() - start_time)
        assert slot >= len(meters) - 1
        meters.extend([0] * (slot - len(meters) + 1))
        meters[-1] += size

    def output_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.output_meters)

    def input_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.input_meters)

    def __bandwidths(self, meters: list[int]) -> pandas.Series:
        return pandas.Series(meters, name="bandwidth")
