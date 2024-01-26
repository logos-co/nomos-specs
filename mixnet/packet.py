from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from itertools import batched
from typing import Dict, Iterator, List, Self, Tuple, TypeAlias

from pysphinx.payload import Payload
from pysphinx.sphinx import SphinxPacket

from mixnet.mixnet import Mixnet, MixNode


class MessageFlag(Enum):
    MESSAGE_FLAG_REAL = b"\x00"
    MESSAGE_FLAG_DROP_COVER = b"\x01"

    def bytes(self) -> bytes:
        return bytes(self.value)


class PacketBuilder:
    iter: Iterator[Tuple[SphinxPacket, List[MixNode]]]

    def __init__(
        self,
        flag: MessageFlag,
        message: bytes,
        mixnet: Mixnet,
    ):
        topology = mixnet.topology
        destination = topology.choose_mix_destionation()

        msg_with_flag = flag.bytes() + message
        # NOTE: We don't encrypt msg_with_flag for destination.
        # If encryption is needed, a shared secret must be appended in front of the message along with the MessageFlag.
        fragment_set = FragmentSet(msg_with_flag)

        packets_and_routes = []
        for fragment in fragment_set.fragments:
            route = topology.generate_route()
            packet = SphinxPacket.build(
                fragment.bytes(),
                [mixnode.sphinx_node() for mixnode in route],
                destination.sphinx_node(),
            )
            packets_and_routes.append((packet, route))

        self.iter = iter(packets_and_routes)

    @classmethod
    def real(cls, message: bytes, mixnet: Mixnet) -> Self:
        return cls(MessageFlag.MESSAGE_FLAG_REAL, message, mixnet)

    @classmethod
    def drop_cover(cls, message: bytes, mixnet: Mixnet) -> Self:
        return cls(MessageFlag.MESSAGE_FLAG_DROP_COVER, message, mixnet)

    def next(self) -> Tuple[SphinxPacket, List[MixNode]]:
        return next(self.iter)

    @staticmethod
    def parse_msg_and_flag(data: bytes) -> Tuple[MessageFlag, bytes]:
        """Remove a MessageFlag from data"""
        if len(data) < 1:
            raise ValueError("data is too short")

        return (MessageFlag(data[0:1]), data[1:])


# Unlikely, Nym uses i32 for FragmentSetId, which may cause more collisions.
# We will use UUID until figuring out why Nym uses i32.
FragmentSetId: TypeAlias = bytes  # 128bit UUID v4
FragmentId: TypeAlias = int  # unsigned 8bit int in big endian

FRAGMENT_SET_ID_LENGTH: int = 16
FRAGMENT_ID_LENGTH: int = 1


@dataclass
class FragmentHeader:
    """
    Contain all information for reconstructing a message that was fragmented into the same FragmentSet.
    """

    set_id: FragmentSetId
    total_fragments: FragmentId
    fragment_id: FragmentId

    SIZE: int = FRAGMENT_SET_ID_LENGTH + FRAGMENT_ID_LENGTH * 2

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
        if len(data) != cls.SIZE:
            raise ValueError("Invalid data length", len(data))

        return cls(data[:16], int.from_bytes(data[16:17]), int.from_bytes(data[17:18]))


@dataclass
class FragmentSet:
    """
    Represent a set of Fragments that can be reconstructed to a single original message.

    Note that the maximum number of fragments in a FragmentSet is limited for now.
    """

    fragments: List[Fragment]

    MAX_FRAGMENTS: int = FragmentHeader.max_total_fragments()

    def __init__(self, message: bytes):
        """
        Build a FragmentSet by chunking a message into Fragments.
        """
        chunked_messages = chunks(message, Fragment.MAX_PAYLOAD_SIZE)
        # For now, we don't support more than max_fragments() fragments.
        # If needed, we can devise the FragmentSet chaining to support larger messages, like Nym.
        if len(chunked_messages) > self.MAX_FRAGMENTS:
            raise ValueError(f"Too long message: {len(chunked_messages)} chunks")

        set_id = uuid.uuid4().bytes
        self.fragments = [
            Fragment(FragmentHeader(set_id, len(chunked_messages), i), chunk)
            for i, chunk in enumerate(chunked_messages)
        ]


@dataclass
class Fragment:
    """Represent a piece of data that can be transformed to a single SphinxPacket"""

    header: FragmentHeader
    body: bytes

    MAX_PAYLOAD_SIZE: int = Payload.max_plain_payload_size() - FragmentHeader.SIZE

    def bytes(self) -> bytes:
        return self.header.bytes() + self.body

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        header = FragmentHeader.from_bytes(data[: FragmentHeader.SIZE])
        body = data[FragmentHeader.SIZE :]
        return cls(header, body)


@dataclass
class MessageReconstructor:
    fragmentSets: Dict[FragmentSetId, FragmentSetReconstructor]

    def __init__(self):
        self.fragmentSets = {}

    def add(self, fragment: Fragment) -> bytes | None:
        if fragment.header.set_id not in self.fragmentSets:
            self.fragmentSets[fragment.header.set_id] = FragmentSetReconstructor(
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

    def __init__(self, total_fragments: FragmentId):
        self.total_fragments = total_fragments
        self.fragments = {}

    def add(self, fragment: Fragment) -> bytes | None:
        self.fragments[fragment.header.fragment_id] = fragment
        if len(self.fragments) == self.total_fragments:
            return self.build_message()
        else:
            return None

    def build_message(self) -> bytes:
        message = b""
        for i in range(self.total_fragments):
            message += self.fragments[FragmentId(i)].body
        return message


def chunks(data: bytes, size: int) -> List[bytes]:
    return list(map(bytes, batched(data, size)))
