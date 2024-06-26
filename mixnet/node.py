from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, TypeAlias

from pysphinx.payload import DEFAULT_PAYLOAD_SIZE
from pysphinx.sphinx import (
    Payload,
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
)

from mixnet.config import MixMembership, NodeConfig
from mixnet.packet import Fragment, MessageFlag, MessageReconstructor, PacketBuilder

NetworkPacket: TypeAlias = "SphinxPacket | bytes"
NetworkPacketQueue: TypeAlias = "asyncio.Queue[NetworkPacket]"
Connection: TypeAlias = NetworkPacketQueue
BroadcastChannel: TypeAlias = "asyncio.Queue[bytes]"


class Node:
    config: NodeConfig
    membership: MixMembership
    mixgossip_channel: MixGossipChannel
    reconstructor: MessageReconstructor
    broadcast_channel: BroadcastChannel

    def __init__(self, config: NodeConfig, membership: MixMembership):
        self.config = config
        self.membership = membership
        self.mixgossip_channel = MixGossipChannel(self.__process_sphinx_packet)
        self.reconstructor = MessageReconstructor()
        self.broadcast_channel = asyncio.Queue()

    async def __process_sphinx_packet(
        self, packet: SphinxPacket
    ) -> NetworkPacket | None:
        try:
            processed = packet.process(self.config.private_key)
            match processed:
                case ProcessedForwardHopPacket():
                    return processed.next_packet
                case ProcessedFinalHopPacket():
                    await self.__process_sphinx_payload(processed.payload)
        except Exception:
            # Return SphinxPacket as it is, if this node cannot unwrap it.
            return packet

    async def __process_sphinx_payload(self, payload: Payload):
        msg_with_flag = self.reconstructor.add(
            Fragment.from_bytes(payload.recover_plain_playload())
        )
        if msg_with_flag is not None:
            flag, msg = PacketBuilder.parse_msg_and_flag(msg_with_flag)
            if flag == MessageFlag.MESSAGE_FLAG_REAL:
                await self.broadcast_channel.put(msg)

    def connect(self, peer: Node):
        conn = asyncio.Queue()
        peer.mixgossip_channel.add_inbound(conn)
        self.mixgossip_channel.add_outbound(
            MixOutboundConnection(conn, self.config.transmission_rate_per_sec)
        )

    async def send_message(self, msg: bytes):
        for packet, _ in PacketBuilder.build_real_packets(msg, self.membership):
            await self.mixgossip_channel.gossip(packet)


class MixGossipChannel:
    inbound_conns: list[Connection]
    outbound_conns: list[MixOutboundConnection]
    handler: Callable[[SphinxPacket], Awaitable[NetworkPacket | None]]

    def __init__(
        self,
        handler: Callable[[SphinxPacket], Awaitable[NetworkPacket | None]],
    ):
        self.inbound_conns = []
        self.outbound_conns = []
        self.handler = handler
        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks = set()

    def add_inbound(self, conn: Connection):
        self.inbound_conns.append(conn)
        task = asyncio.create_task(self.__process_inbound_conn(conn))
        self.tasks.add(task)
        # To discard the task from the set automatically when it is done.
        task.add_done_callback(self.tasks.discard)

    def add_outbound(self, conn: MixOutboundConnection):
        self.outbound_conns.append(conn)

    async def __process_inbound_conn(self, conn: Connection):
        while True:
            elem = await conn.get()
            if isinstance(elem, bytes):
                assert elem == build_noise_packet()
                # Drop packet
                continue
            elif isinstance(elem, SphinxPacket):
                net_packet = await self.handler(elem)
                if net_packet is not None:
                    await self.gossip(net_packet)

    async def gossip(self, packet: NetworkPacket):
        for conn in self.outbound_conns:
            await conn.send(packet)


class MixOutboundConnection:
    queue: NetworkPacketQueue
    conn: Connection
    transmission_rate_per_sec: int

    def __init__(self, conn: Connection, transmission_rate_per_sec: int):
        self.queue = asyncio.Queue()
        self.conn = conn
        self.transmission_rate_per_sec = transmission_rate_per_sec
        self.task = asyncio.create_task(self.__run())

    async def __run(self):
        while True:
            await asyncio.sleep(1 / self.transmission_rate_per_sec)
            # TODO: time mixing
            if self.queue.empty():
                elem = build_noise_packet()
            else:
                elem = self.queue.get_nowait()
            await self.conn.put(elem)

    async def send(self, elem: NetworkPacket):
        await self.queue.put(elem)


def build_noise_packet() -> bytes:
    return bytes(DEFAULT_PAYLOAD_SIZE)
