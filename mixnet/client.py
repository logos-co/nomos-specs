from __future__ import annotations

import asyncio

from mixnet.mixnet import Mixnet, MixnetTopology
from mixnet.node import PacketQueue
from mixnet.packet import PacketBuilder
from mixnet.poisson import poisson_interval_sec


async def mixclient_emitter(
    mixnet: Mixnet,
    topology: MixnetTopology,
    emission_rate_per_min: int,  # Poisson rate parameter: lambda in the spec
    redundancy: int,  # b in the spec
    real_packet_queue: PacketQueue,
    outbound_socket: PacketQueue,
):
    """
    Emit packets at the Poisson emission_rate_per_min.

    If a real packet is scheduled to be sent, this thread sends the real packet to the mixnet,
    and schedules redundant real packets to be emitted in the next turns.

    If no real packet is not scheduled, this thread emits a cover packet according to the emission_rate_per_min.
    """

    redundant_real_packet_queue: PacketQueue = asyncio.Queue()

    emission_notifier_queue = asyncio.Queue()
    _ = asyncio.create_task(
        emission_notifier(emission_rate_per_min, emission_notifier_queue)
    )

    while True:
        # Wait until the next emission time
        _ = await emission_notifier_queue.get()
        try:
            await emit(
                mixnet,
                topology,
                redundancy,
                real_packet_queue,
                redundant_real_packet_queue,
                outbound_socket,
            )
        finally:
            # Python convention: indicate that the previously enqueued task has been processed
            emission_notifier_queue.task_done()


async def emit(
    mixnet: Mixnet,
    topology: MixnetTopology,
    redundancy: int,  # b in the spec
    real_packet_queue: PacketQueue,
    redundant_real_packet_queue: PacketQueue,
    outbound_socket: PacketQueue,
):
    if not redundant_real_packet_queue.empty():
        addr, packet = redundant_real_packet_queue.get_nowait()
        await outbound_socket.put((addr, packet))
        return

    if not real_packet_queue.empty():
        addr, packet = real_packet_queue.get_nowait()
        # Schedule redundant real packets
        for _ in range(redundancy - 1):
            redundant_real_packet_queue.put_nowait((addr, packet))
            await outbound_socket.put((addr, packet))

    packet, route = PacketBuilder.drop_cover(b"drop cover", mixnet, topology).next()
    await outbound_socket.put((route[0].addr, packet))


async def emission_notifier(emission_rate_per_min: int, queue: asyncio.Queue):
    while True:
        await asyncio.sleep(poisson_interval_sec(emission_rate_per_min))
        queue.put_nowait(None)
