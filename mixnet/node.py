from __future__ import annotations

import hashlib
from enum import Enum
from typing import Awaitable, Callable, TypeAlias

from pysphinx.payload import DEFAULT_PAYLOAD_SIZE
from pysphinx.sphinx import (
    Payload,
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
)

from mixnet.config import GlobalConfig, NodeConfig
from mixnet.connection import SimplexConnection
from mixnet.framework.framework import Framework, Queue
from mixnet.packet import Fragment, MessageFlag, MessageReconstructor, PacketBuilder

NetworkPacketQueue: TypeAlias = Queue
BroadcastChannel: TypeAlias = Queue


class Node:
    framework: Framework
    config: NodeConfig
    global_config: GlobalConfig
    mixgossip_channel: MixGossipChannel
    reconstructor: MessageReconstructor
    broadcast_channel: BroadcastChannel

    def __init__(
        self, framework: Framework, config: NodeConfig, global_config: GlobalConfig
    ):
        self.framework = framework
        self.config = config
        self.global_config = global_config
        self.mixgossip_channel = MixGossipChannel(
            framework, config.peering_degree, self.__process_sphinx_packet
        )
        self.reconstructor = MessageReconstructor()
        self.broadcast_channel = framework.queue()

    async def __process_sphinx_packet(
        self, packet: SphinxPacket
    ) -> SphinxPacket | None:
        try:
            processed = packet.process(self.config.private_key)
            match processed:
                case ProcessedForwardHopPacket():
                    return processed.next_packet
                case ProcessedFinalHopPacket():
                    await self.__process_sphinx_payload(processed.payload)
        except ValueError:
            # Return SphinxPacket as it is, if it cannot be unwrapped by the private key of this node.
            return packet

    async def __process_sphinx_payload(self, payload: Payload):
        msg_with_flag = self.reconstructor.add(
            Fragment.from_bytes(payload.recover_plain_playload())
        )
        if msg_with_flag is not None:
            flag, msg = PacketBuilder.parse_msg_and_flag(msg_with_flag)
            if flag == MessageFlag.MESSAGE_FLAG_REAL:
                print(f"{self.config.id(True)}: Broadcasting message finally: {msg}")
                await self.broadcast_channel.put(msg)

    def connect(
        self,
        peer: Node,
        inbound_conn: SimplexConnection,
        outbound_conn: SimplexConnection,
    ):
        if (
            not self.mixgossip_channel.can_accept_conn()
            or not peer.mixgossip_channel.can_accept_conn()
        ):
            raise PeeringDegreeReached

        self.mixgossip_channel.add_conn(
            DuplexConnection(
                inbound_conn,
                MixSimplexConnection(
                    self.framework,
                    outbound_conn,
                    self.global_config.transmission_rate_per_sec,
                ),
            )
        )
        peer.mixgossip_channel.add_conn(
            DuplexConnection(
                outbound_conn,
                MixSimplexConnection(
                    self.framework,
                    inbound_conn,
                    self.global_config.transmission_rate_per_sec,
                ),
            )
        )

    async def send_message(self, msg: bytes):
        print(f"{self.config.id(True)}: Sending message: {msg}")
        for packet, _ in PacketBuilder.build_real_packets(
            msg, self.global_config.membership
        ):
            await self.mixgossip_channel.gossip(build_msg(MsgType.REAL, packet.bytes()))


class MixGossipChannel:
    framework: Framework
    peering_degree: int
    conns: list[DuplexConnection]
    handler: Callable[[SphinxPacket], Awaitable[SphinxPacket | None]]
    msg_cache: set[bytes]

    def __init__(
        self,
        framework: Framework,
        peering_degree: int,
        handler: Callable[[SphinxPacket], Awaitable[SphinxPacket | None]],
    ):
        self.framework = framework
        self.peering_degree = peering_degree
        self.conns = []
        self.handler = handler
        self.msg_cache = set()
        # A set just for gathering a reference of tasks to prevent them from being garbage collected.
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        self.tasks = set()

    def can_accept_conn(self) -> bool:
        return len(self.conns) < self.peering_degree

    def add_conn(self, conn: DuplexConnection):
        if not self.can_accept_conn():
            # For simplicity of the spec, reject the connection if the peering degree is reached.
            raise PeeringDegreeReached()

        self.conns.append(conn)
        task = self.framework.spawn(self.__process_inbound_conn(conn))
        self.tasks.add(task)

    async def __process_inbound_conn(self, conn: DuplexConnection):
        while True:
            msg = await conn.recv()
            # Don't process the same message twice.
            msg_hash = hashlib.sha256(msg).digest()
            if msg_hash in self.msg_cache:
                continue
            self.msg_cache.add(msg_hash)

            flag, msg = parse_msg(msg)
            match flag:
                case MsgType.NOISE:
                    # Drop noise packet
                    continue
                case MsgType.REAL:
                    # Handle the packet and gossip the result if needed.
                    sphinx_packet = SphinxPacket.from_bytes(msg)
                    new_sphinx_packet = await self.handler(sphinx_packet)
                    if new_sphinx_packet is not None:
                        await self.gossip(
                            build_msg(MsgType.REAL, new_sphinx_packet.bytes())
                        )

    async def gossip(self, packet: bytes):
        for conn in self.conns:
            await conn.send(packet)


class DuplexConnection:
    inbound: SimplexConnection
    outbound: MixSimplexConnection

    def __init__(self, inbound: SimplexConnection, outbound: MixSimplexConnection):
        self.inbound = inbound
        self.outbound = outbound

    async def recv(self) -> bytes:
        return await self.inbound.recv()

    async def send(self, packet: bytes):
        await self.outbound.send(packet)


class MixSimplexConnection:
    framework: Framework
    queue: NetworkPacketQueue
    conn: SimplexConnection
    transmission_rate_per_sec: float

    def __init__(
        self,
        framework: Framework,
        conn: SimplexConnection,
        transmission_rate_per_sec: float,
    ):
        self.framework = framework
        self.queue = framework.queue()
        self.conn = conn
        self.transmission_rate_per_sec = transmission_rate_per_sec
        self.task = framework.spawn(self.__run())

    async def __run(self):
        while True:
            await self.framework.sleep(1 / self.transmission_rate_per_sec)
            # TODO: time mixing
            if self.queue.empty():
                elem = build_noise_packet()
            else:
                elem = await self.queue.get()
            await self.conn.send(elem)

    async def send(self, elem: bytes):
        await self.queue.put(elem)


class MsgType(Enum):
    REAL = b"\x00"
    NOISE = b"\x01"


def build_msg(flag: MsgType, data: bytes) -> bytes:
    return flag.value + data


def parse_msg(data: bytes) -> tuple[MsgType, bytes]:
    if len(data) < 1:
        raise ValueError("Invalid message format")
    return (MsgType(data[:1]), data[1:])


def build_noise_packet() -> bytes:
    return build_msg(MsgType.NOISE, bytes(DEFAULT_PAYLOAD_SIZE))


class PeeringDegreeReached(Exception):
    pass
