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
    """
    This represents any node in the network, which:
    - generates/gossips mix messages (Sphinx packets)
    - performs cryptographic mix (unwrapping Sphinx packets)
    - generates noise
    """

    config: NodeConfig
    global_config: GlobalConfig
    mixgossip_channel: GossipChannel
    reconstructor: MessageReconstructor
    broadcast_channel: BroadcastChannel
    # The actual packet size is calculated based on the max length of mix path by Sphinx encoding
    # when the node is initialized, so that it can be used to generate noise packets.
    packet_size: int

    def __init__(self, config: NodeConfig, global_config: GlobalConfig):
        self.config = config
        self.global_config = global_config
        self.mixgossip_channel = GossipChannel(config.gossip, self.__process_msg)
        self.reconstructor = MessageReconstructor()
        self.broadcast_channel = asyncio.Queue()

        sample_packet, _ = PacketBuilder.build_real_packets(
            bytes(1), global_config.membership, self.global_config.max_mix_path_length
        )[0]
        self.packet_size = len(sample_packet.bytes())

    async def __process_msg(self, msg: bytes) -> bytes | None:
        """
        A handler to process messages received via gossip channel
        """
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
        """
        Unwrap the Sphinx packet and process the next Sphinx packet or the payload.
        """
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
        """
        Process the Sphinx payload and broadcast it if it is a real message.
        """
        msg_with_flag = self.reconstructor.add(
            Fragment.from_bytes(payload.recover_plain_playload())
        )
        if msg_with_flag is not None:
            flag, msg = PacketBuilder.parse_msg_and_flag(msg_with_flag)
            if flag == MessageFlag.MESSAGE_FLAG_REAL:
                await self.broadcast_channel.put(msg)

    def connect(self, peer: Node):
        """
        Establish a duplex connection with a peer node.
        """
        noise_msg = Node.__build_msg(MsgType.NOISE, bytes(self.packet_size))
        inbound_conn, outbound_conn = asyncio.Queue(), asyncio.Queue()

        # Register a duplex connection for its own use
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
        # Register the same duplex connection for the peer
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
        """
        Build a Sphinx packet and gossip it to all connected peers.
        """
        # Here, we handle the case in which a msg is split into multiple Sphinx packets.
        # But, in practice, we expect a message to be small enough to fit in a single Sphinx packet.
        for packet, _ in PacketBuilder.build_real_packets(
            msg,
            self.global_config.membership,
            self.config.mix_path_length,
        ):
            await self.mixgossip_channel.gossip(
                Node.__build_msg(MsgType.REAL, packet.bytes())
            )

    @staticmethod
    def __build_msg(flag: MsgType, data: bytes) -> bytes:
        """
        Prepend a flag to the message, right before sending it via network channel.
        """
        return flag.value + data

    @staticmethod
    def __parse_msg(data: bytes) -> tuple[MsgType, bytes]:
        """
        Parse the message and extract the flag.
        """
        if len(data) < 1:
            raise ValueError("Invalid message format")
        return (MsgType(data[:1]), data[1:])


class MsgType(Enum):
    REAL = b"\x00"
    NOISE = b"\x01"
