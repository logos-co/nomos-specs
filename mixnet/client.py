from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Self

from mixnet.config import MixnetConfig
from mixnet.node import PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec


class MixClient:
    __config: MixnetConfig

    __real_packet_queue: PacketQueue
    __outbound_socket: PacketQueue
    __task: asyncio.Task  # A reference just to prevent task from being garbage collected

    @classmethod
    async def new(
        cls,
        config: MixnetConfig,
    ) -> Self:
        self = cls()
        self.__config = config
        self.__real_packet_queue = asyncio.Queue()
        self.__outbound_socket = asyncio.Queue()
        self.__task = asyncio.create_task(self.__run())
        return self

    def set_config(self, config: MixnetConfig) -> None:
        """
        Replace the old config with the new config received

        In real implementations, this method may be integrated in a long-running task.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__config = config

    def get_config(self) -> MixnetConfig:
        return self.__config

    async def send_message(self, msg: bytes) -> None:
        packets_and_routes = PacketBuilder.build_real_packets(
            msg, self.__config.topology
        )
        for packet, route in packets_and_routes:
            await self.__real_packet_queue.put((route[0].addr, packet))

    def subscribe_messages(self) -> "asyncio.Queue[bytes]":
        """
        Subscribe messages, which went through mix nodes and were broadcasted via gossip
        """
        return asyncio.Queue()

    @property
    def outbound_socket(self) -> PacketQueue:
        return self.__outbound_socket

    async def __run(self):
        """
        Emit packets at the Poisson emission_rate_per_min.

        If a real packet is scheduled to be sent, this thread sends the real packet to the mixnet,
        and schedules redundant real packets to be emitted in the next turns.

        If no real packet is not scheduled, this thread emits a cover packet according to the emission_rate_per_min.
        """

        redundant_real_packet_queue: PacketQueue = asyncio.Queue()

        emission_notifier_queue = asyncio.Queue()
        _ = asyncio.create_task(
            self.__emission_notifier(
                self.__config.emission_rate_per_min, emission_notifier_queue
            )
        )

        while True:
            # Wait until the next emission time
            _ = await emission_notifier_queue.get()
            try:
                await self.__emit(self.__config.redundancy, redundant_real_packet_queue)
            finally:
                # Python convention: indicate that the previously enqueued task has been processed
                emission_notifier_queue.task_done()

    async def __emit(
        self,
        redundancy: int,  # b in the spec
        redundant_real_packet_queue: PacketQueue,
    ):
        if not redundant_real_packet_queue.empty():
            addr, packet = redundant_real_packet_queue.get_nowait()
            await self.__outbound_socket.put((addr, packet))
            return

        if not self.__real_packet_queue.empty():
            addr, packet = self.__real_packet_queue.get_nowait()
            # Schedule redundant real packets
            for _ in range(redundancy - 1):
                redundant_real_packet_queue.put_nowait((addr, packet))
                await self.__outbound_socket.put((addr, packet))

        packets_and_routes = PacketBuilder.build_drop_cover_packets(
            b"drop cover", self.__config.topology
        )
        # We have a for loop here, but we expect that the total num of packets is 1
        # because the dummy message is short.
        for packet, route in packets_and_routes:
            await self.__outbound_socket.put((route[0].addr, packet))

    async def __emission_notifier(
        self, emission_rate_per_min: int, queue: asyncio.Queue
    ):
        while True:
            await asyncio.sleep(poisson_interval_sec(emission_rate_per_min))
            queue.put_nowait(None)

    async def cancel(self) -> None:
        self.__task.cancel()
        with suppress(asyncio.CancelledError):
            await self.__task
