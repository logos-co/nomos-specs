from __future__ import annotations

import asyncio

NetworkPacketQueue = asyncio.Queue[bytes]
SimplexConnection = NetworkPacketQueue


class DuplexConnection:
    """
    A duplex connection in which data can be transmitted and received simultaneously in both directions.
    This is to mimic duplex communication in a real network (such as TCP or QUIC).
    """

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
    """
    Wraps a SimplexConnection to add a transmission rate and noise to the connection.
    """

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
            # TODO: temporal mixing
            if self.queue.empty():
                # To guarantee GTR, send noise if there is no message to send
                msg = self.noise_msg
            else:
                msg = self.queue.get_nowait()
            await self.conn.put(msg)

    async def send(self, msg: bytes):
        await self.queue.put(msg)
