from __future__ import annotations

import abc

from mixnet.framework import Framework, Queue

NetworkPacketQueue = Queue


class SimplexConnection(abc.ABC):
    """
    An abstract class for a simplex connection that can send and receive data in one direction
    """

    @abc.abstractmethod
    async def send(self, data: bytes) -> None:
        pass

    @abc.abstractmethod
    async def recv(self) -> bytes:
        pass


class LocalSimplexConnection(SimplexConnection):
    """
    A simplex connection that doesn't have any network latency.
    Data sent through this connection can be immediately received from the other end.
    """

    def __init__(self, framework: Framework):
        self.queue = framework.queue()

    async def send(self, data: bytes) -> None:
        await self.queue.put(data)

    async def recv(self) -> bytes:
        return await self.queue.get()


class DuplexConnection:
    """
    A duplex connection in which data can be transmitted and received simultaneously in both directions.
    This is to mimic duplex communication in a real network (such as TCP or QUIC).
    """

    def __init__(self, inbound: SimplexConnection, outbound: MixSimplexConnection):
        self.inbound = inbound
        self.outbound = outbound

    async def recv(self) -> bytes:
        return await self.inbound.recv()

    async def send(self, packet: bytes):
        await self.outbound.send(packet)


class MixSimplexConnection:
    """
    Wraps a SimplexConnection to add a transmission rate and noise to the connection.
    """

    def __init__(
        self,
        framework: Framework,
        conn: SimplexConnection,
        transmission_rate_per_sec: int,
        noise_msg: bytes,
    ):
        self.framework = framework
        self.queue = framework.queue()
        self.conn = conn
        self.transmission_rate_per_sec = transmission_rate_per_sec
        self.noise_msg = noise_msg
        self.task = framework.spawn(self.__run())

    async def __run(self):
        while True:
            await self.framework.sleep(1 / self.transmission_rate_per_sec)
            # TODO: temporal mixing
            if self.queue.empty():
                # To guarantee GTR, send noise if there is no message to send
                msg = self.noise_msg
            else:
                msg = await self.queue.get()
            await self.conn.send(msg)

    async def send(self, msg: bytes):
        await self.queue.put(msg)
