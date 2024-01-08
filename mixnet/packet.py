from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Dict, List, Self, Tuple, TypeAlias

from mixnet.mixnet import Mixnet, MixnetTopology, MixNode
from mixnet.sphinx.payload import Payload
from mixnet.sphinx.sphinx import SphinxPacket

MessageFlag: TypeAlias = bytes  # 1byte

MESSAGE_FLAG_REAL: MessageFlag = b"\x00"
MESSAGE_FLAG_DROP_COVER: MessageFlag = b"\x01"


class PacketBuilder:
    """Build a real packet or a drop cover packet."""

    @staticmethod
    def build_real_packets(
        message: bytes, mixnet: Mixnet, topology: MixnetTopology
    ) -> Tuple[List[SphinxPacket], List[List[MixNode]]]:
        """Build real SphinxPackets and return them with a list of mix routes chosen for each SphinxPacket respectively."""
        destination = mixnet.choose_mixnode()

        msg_with_flag = MESSAGE_FLAG_REAL + message
        # NOTE: We don't encrypt msg_with_flag for destination.
        # If encryption is needed, a shared secret must be appended in front of the message along with the MessageFlag.
        fragment_set = FragmentSet(msg_with_flag)

        packets = []
        routes = []
        for fragment in fragment_set.fragments:
            route = topology.generate_route()
            packets.append(SphinxPacket.build(fragment.bytes(), route, destination))
            routes.append(route)
        return packets, routes

    @staticmethod
    def build_drop_cover_packet(
        mixnet: Mixnet, topology: MixnetTopology
    ) -> Tuple[SphinxPacket, List[MixNode]]:
        """Bulid a drop cover SphinxPacket and return it with a mix route chosen"""
        destination = mixnet.choose_mixnode()

        msg_with_flag = MESSAGE_FLAG_DROP_COVER + b""
        # NOTE: We don't encrypt msg_with_flag for destination.
        # If encryption is needed, a shared secret must be appended in front of the message along with the MessageFlag.
        fragment_set = FragmentSet(msg_with_flag)
        # Since a drop cover message is very small (1byte + padding),
        # it should fit in a single fragment.
        assert len(fragment_set.fragments) == 1

        route = topology.generate_route()
        return (
            SphinxPacket.build(fragment_set.fragments[0].bytes(), route, destination),
            route,
        )

    @staticmethod
    def parse_msg_and_flag(data: bytes) -> Tuple[MessageFlag, bytes]:
        """Remove a MessageFlag from data"""
        assert len(data) >= 1
        return (data[0:1], data[1:])


@dataclass
class FragmentSet:
    """
    Represent a set of Fragments that can be reconstructed to a single original message.

    Note that the maximum number of fragments in a FragmentSet is limited for now.
    """

    fragments: List[Fragment]

    def __init__(self, message: bytes):
        """
        Build a FragmentSet by chunking a message into Fragments.
        """
        chunked_messages = chunks(message, Fragment.max_payload_size())
        # For now, we don't support more than max_fragments() fragments.
        # If needed, we can devise the FragmentSet chaining to support larger messages, like Nym.
        assert len(chunked_messages) <= self.max_fragments()

        set_id = uuid.uuid4().bytes
        fragments = []
        for i, chunk in enumerate(chunked_messages):
            fragments.append(
                Fragment(
                    FragmentHeader(set_id, len(chunked_messages), i),
                    chunk,
                )
            )

        self.fragments = fragments

    @staticmethod
    def max_fragments() -> int:
        return FragmentHeader.max_total_fragments()


@dataclass
class Fragment:
    """Represent a piece of data that can be transformed to a single SphinxPacket"""

    header: FragmentHeader
    body: bytes

    @staticmethod
    def max_payload_size() -> int:
        return Payload.max_plain_payload_size() - FragmentHeader.size()

    def bytes(self) -> bytes:
        return self.header.bytes() + self.body

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        header = FragmentHeader.from_bytes(data[: FragmentHeader.size()])
        body = data[FragmentHeader.size() :]
        return cls(header, body)


# Unlikely, Nym uses i32 for FragmentSetId, which may cause more collisions.
# We will use UUID until figuring out why Nym uses i32.
FragmentSetId: TypeAlias = bytes  # 128bit UUID v4
FragmentId: TypeAlias = int  # unsigned 8bit int in big endian


@dataclass
class FragmentHeader:
    """
    Contain all information for reconstructing a message that was fragmented into the same FragmentSet.
    """

    set_id: FragmentSetId
    total_fragments: FragmentId
    fragment_id: FragmentId

    @staticmethod
    def size() -> int:
        return 16 + 1 + 1

    @staticmethod
    def max_total_fragments() -> int:
        return 256  # because total_fragment is u8

    def bytes(self) -> bytes:
        return (
            self.set_id
            + self.total_fragments.to_bytes(1)
            + self.fragment_id.to_bytes(1)
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        assert len(data) == cls.size()
        return cls(data[:16], int.from_bytes(data[16:17]), int.from_bytes(data[17:18]))


@dataclass
class MessageReconstructor:
    fragmentSets: Dict[FragmentSetId, FragmentSetReconstructor]

    @classmethod
    def new(cls) -> Self:
        return cls({})

    def add(self, fragment: Fragment) -> bytes | None:
        if fragment.header.set_id not in self.fragmentSets:
            self.fragmentSets[fragment.header.set_id] = FragmentSetReconstructor.new(
                fragment.header.total_fragments
            )

        msg = self.fragmentSets[fragment.header.set_id].add(fragment)
        if msg is not None:
            del self.fragmentSets[fragment.header.set_id]
        return msg


@dataclass
class FragmentSetReconstructor:
    total_fragments: FragmentId
    fragments: Dict[FragmentId, Fragment]

    @classmethod
    def new(cls, total_fragments: FragmentId) -> Self:
        return cls(total_fragments, {})

    def add(self, fragment: Fragment) -> bytes | None:
        self.fragments[fragment.header.fragment_id] = fragment
        if len(self.fragments) == self.total_fragments:
            message = b""
            for i in range(self.total_fragments):
                message += self.fragments[FragmentId(i)].body
            return message
        else:
            return None


def chunks(data: bytes, size: int) -> List[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)]
