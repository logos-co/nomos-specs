from dataclasses import dataclass
from itertools import chain, zip_longest
from typing import List, Generator, Self

from eth2spec.eip7594.mainnet import Bytes32


class NodeId(Bytes32):
    pass

class Chunk(Bytes32):
    pass


class Column(List[Bytes32]):
    def as_bytes(self) -> bytes:
        return bytes(chain.from_iterable(self))


class Row(List[Bytes32]):
    def as_bytes(self) -> bytes:
        return bytes(chain.from_iterable(self))


class ChunksMatrix(List[Row | Column]):
    @property
    def columns(self) -> Generator[List[Chunk], None, None]:
        yield from map(Column, zip_longest(*self, fillvalue=b""))

    def transposed(self) -> Self:
        return ChunksMatrix(self.columns)


BLSPublickey = bytes
BLSPrivateKey = int
BLSSignature = bytes


@dataclass
class Attestation:
    signature: BLSSignature


@dataclass
class Certificate:
    pass

