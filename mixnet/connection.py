from __future__ import annotations

import asyncio

NetworkPacketQueue = asyncio.Queue[bytes]
SimplexConnection = NetworkPacketQueue


class DuplexConnection:
    inbound: SimplexConnection
    outbound: MixSimplexConnection

    def __init__(self, inbound: SimplexConnection, outbound: MixSimplexConnection):
        self.inbound = inbound
        self.outbound = outbound

    async def recv(self) -> bytes:
        return await self.inbound.get()

    async def send(self, packet: bytes):
        await self.outbound.send(packet)


class MixSimplexConnection:
    queue: NetworkPacketQueue
    conn: SimplexConnection
    transmission_rate_per_sec: int
    noise_msg: bytes

    def __init__(
        self, conn: SimplexConnection, transmission_rate_per_sec: int, noise_msg: bytes
    ):
        self.queue = asyncio.Queue()
        self.conn = conn
        self.transmission_rate_per_sec = transmission_rate_per_sec
        self.noise_msg = noise_msg
        self.task = asyncio.create_task(self.__run())

    async def __run(self):
        while True:
            await asyncio.sleep(1 / self.transmission_rate_per_sec)
            # TODO: time mixing
            if self.queue.empty():
                elem = self.noise_msg
            else:
                elem = self.queue.get_nowait()
            await self.conn.put(elem)

    async def send(self, elem: bytes):
        await self.queue.put(elem)
