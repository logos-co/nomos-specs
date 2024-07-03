import asyncio
import math
import time

import pandas

from mixnet.connection import SimplexConnection


class MeteredRemoteSimplexConnection(SimplexConnection):
    latency: float
    meter_interval: float
    outputs: asyncio.Queue
    conn: asyncio.Queue
    inputs: asyncio.Queue
    output_task: asyncio.Task
    output_meters: list[int]
    input_task: asyncio.Task
    input_meters: list[int]

    def __init__(self, latency: float, meter_interval: float):
        self.latency = latency
        self.meter_interval = meter_interval
        self.outputs = asyncio.Queue()
        self.conn = asyncio.Queue()
        self.inputs = asyncio.Queue()
        self.output_meters = []
        self.output_task = asyncio.create_task(self.__run_output_task())
        self.input_meters = []
        self.input_task = asyncio.create_task(self.__run_input_task())

    async def send(self, data: bytes) -> None:
        await self.outputs.put(data)

    async def recv(self) -> bytes:
        return await self.inputs.get()

    async def __run_output_task(self):
        start_time = time.time()
        while True:
            data = await self.outputs.get()
            self.__update_meter(self.output_meters, len(data), start_time)
            await self.conn.put(data)

    async def __run_input_task(self):
        start_time = time.time()
        while True:
            await asyncio.sleep(self.latency)
            data = await self.conn.get()
            self.__update_meter(self.input_meters, len(data), start_time)
            await self.inputs.put(data)

    def __update_meter(self, meters: list[int], size: int, start_time: float):
        slot = math.floor((time.time() - start_time) / self.meter_interval)
        assert slot >= len(meters) - 1
        meters.extend([0] * (slot - len(meters) + 1))
        meters[-1] += size

    def output_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.output_meters)

    def input_bandwidths(self) -> pandas.Series:
        return self.__bandwidths(self.input_meters)

    def __bandwidths(self, meters: list[int]) -> pandas.Series:
        return pandas.Series(meters, name="bandwidth").map(
            lambda x: x / self.meter_interval
        )
