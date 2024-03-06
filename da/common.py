from dataclasses import dataclass
from itertools import chain
from typing import List, Generator, Self

from eth2spec.eip7594.mainnet import Bytes32


class NodeId(Bytes32):
    pass

class Chunk(Bytes32):
    pass


class Column(List[Bytes32]):
    pass


class Row(List[Bytes32]):
    def as_bytes(self) -> bytes:
        return bytes(chain.from_iterable(self))


class ChunksMatrix(List[Row]):
    @property
    def columns(self) -> Generator[List[Chunk], None, None]:
        yield from map(Row, zip(*self))

    def transposed(self) -> Self:
        return ChunksMatrix(self.columns)




@dataclass
class Attestation:
    pass


@dataclass
class Certificate:
    pass

