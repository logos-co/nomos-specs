from __future__ import annotations

import asyncio
from typing import TypeAlias

from pysphinx.sphinx import (
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
    SphinxPacket,
)

from mixnet.config import GlobalConfig, NodeConfig
from mixnet.nomssip import Nomssip
from mixnet.sphinx import SphinxPacketBuilder

BroadcastChannel: TypeAlias = asyncio.Queue[bytes]


class Node:
    """
    This represents any node in the network, which:
    - generates/gossips mix messages (Sphinx packets)
    - performs cryptographic mix (unwrapping Sphinx packets)
    - generates noise
    """

    def __init__(self, config: NodeConfig, global_config: GlobalConfig):
        self.config = config
        self.global_config = global_config
        self.nomssip = Nomssip(
            Nomssip.Config(
                global_config.transmission_rate_per_sec,
                config.nomssip.peering_degree,
                self.__calculate_message_size(global_config),
            ),
            self.__process_msg,
        )
        self.broadcast_channel = asyncio.Queue()

    @staticmethod
    def __calculate_message_size(global_config: GlobalConfig) -> int:
        """
        Calculate the actual message size to be gossiped, which depends on the maximum length of mix path.
        """
        sample_sphinx_packet, _ = SphinxPacketBuilder.build(
            bytes(global_config.max_message_size),
            global_config,
            global_config.max_mix_path_length,
        )
        return len(sample_sphinx_packet.bytes())

    async def __process_msg(self, msg: bytes) -> None:
        """
        A handler to process messages received via gossip channel
        """
        sphinx_packet = SphinxPacket.from_bytes(msg)
        result = await self.__process_sphinx_packet(sphinx_packet)
        match result:
            case SphinxPacket():
                # Gossip the next Sphinx packet
                await self.nomssip.gossip(result.bytes())
            case bytes():
                # Broadcast the message fully recovered from Sphinx packets
                await self.broadcast_channel.put(result)
            case None:
                return

    async def __process_sphinx_packet(
        self, packet: SphinxPacket
    ) -> SphinxPacket | bytes | None:
        """
        Unwrap the Sphinx packet and process the next Sphinx packet or the payload if possible
        """
        try:
            processed = packet.process(self.config.private_key)
            match processed:
                case ProcessedForwardHopPacket():
                    return processed.next_packet
                case ProcessedFinalHopPacket():
                    return processed.payload.recover_plain_playload()
        except ValueError:
            # Return nothing, if it cannot be unwrapped by the private key of this node.
            return None

    def connect(self, peer: Node):
        """
        Establish a duplex connection with a peer node.
        """
        inbound_conn, outbound_conn = asyncio.Queue(), asyncio.Queue()
        # Register a duplex connection for its own use
        self.nomssip.add_conn(inbound_conn, outbound_conn)
        # Register a duplex connection for the peer
        peer.nomssip.add_conn(outbound_conn, inbound_conn)

    async def send_message(self, msg: bytes):
        """
        Build a Sphinx packet and gossip it to all connected peers.
        """
        # Here, we handle the case in which a msg is split into multiple Sphinx packets.
        # But, in practice, we expect a message to be small enough to fit in a single Sphinx packet.
        sphinx_packet, _ = SphinxPacketBuilder.build(
            msg,
            self.global_config,
            self.config.mix_path_length,
        )
        await self.nomssip.gossip(sphinx_packet.bytes())
