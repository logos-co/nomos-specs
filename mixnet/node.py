from __future__ import annotations

import asyncio
from enum import Enum
from typing import TypeAlias

from pysphinx.sphinx import (
    Payload,
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
)

from mixnet.config import GlobalConfig, NodeConfig
from mixnet.connection import DuplexConnection, MixSimplexConnection
from mixnet.gossip import GossipChannel
from mixnet.packet import Fragment, MessageFlag, MessageReconstructor, PacketBuilder

BroadcastChannel: TypeAlias = asyncio.Queue[bytes]


class Node:
    config: NodeConfig
    global_config: GlobalConfig
    mixgossip_channel: GossipChannel
    reconstructor: MessageReconstructor
    broadcast_channel: BroadcastChannel
    packet_size: int

    def __init__(self, config: NodeConfig, global_config: GlobalConfig):
        self.config = config
        self.global_config = global_config
        self.mixgossip_channel = GossipChannel(config.gossip, self.__process_msg)
        self.reconstructor = MessageReconstructor()
        self.broadcast_channel = asyncio.Queue()

        sample_packet, _ = PacketBuilder.build_real_packets(
            bytes(1), global_config.membership
        )[0]
        self.packet_size = len(sample_packet.bytes())

    async def __process_msg(self, msg: bytes) -> bytes | None:
        flag, msg = Node.__parse_msg(msg)
        match flag:
            case MsgType.NOISE:
                # Drop noise packet
                return None
            case MsgType.REAL:
                # Handle the packet and gossip the result if needed.
                sphinx_packet = SphinxPacket.from_bytes(msg)
                new_sphinx_packet = await self.__process_sphinx_packet(sphinx_packet)
                if new_sphinx_packet is None:
                    return None
                return Node.__build_msg(MsgType.REAL, new_sphinx_packet.bytes())

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
                await self.broadcast_channel.put(msg)

    def connect(self, peer: Node):
        noise_msg = Node.__build_msg(MsgType.NOISE, bytes(self.packet_size))
        inbound_conn, outbound_conn = asyncio.Queue(), asyncio.Queue()
        self.mixgossip_channel.add_conn(
            DuplexConnection(
                inbound_conn,
                MixSimplexConnection(
                    outbound_conn,
                    self.global_config.transmission_rate_per_sec,
                    noise_msg,
                ),
            )
        )
        peer.mixgossip_channel.add_conn(
            DuplexConnection(
                outbound_conn,
                MixSimplexConnection(
                    inbound_conn,
                    self.global_config.transmission_rate_per_sec,
                    noise_msg,
                ),
            )
        )

    async def send_message(self, msg: bytes):
        for packet, _ in PacketBuilder.build_real_packets(
            msg, self.global_config.membership
        ):
            await self.mixgossip_channel.gossip(
                Node.__build_msg(MsgType.REAL, packet.bytes())
            )

    @staticmethod
    def __build_msg(flag: MsgType, data: bytes) -> bytes:
        return flag.value + data

    @staticmethod
    def __parse_msg(data: bytes) -> tuple[MsgType, bytes]:
        if len(data) < 1:
            raise ValueError("Invalid message format")
        return (MsgType(data[:1]), data[1:])


class MsgType(Enum):
    REAL = b"\x00"
    NOISE = b"\x01"
