from dataclasses import dataclass
from typing import List, Generator
from itertools import chain
from eth2spec.eip7594.mainnet import Bytes32, Blob


class NodeId(Bytes32):
    pass


class Chunk(Bytes32):
    pass


class Column(List[Chunk]):
    pass


class Row(List[Chunk]):
    def as_blob(self) -> Blob:
        return Blob(chain.from_iterable(self))


class ChunksMatrix(List[Row]):
    def columns(self) -> Generator[List[Chunk], None, None]:
        yield from zip(*self)


@dataclass
class Attestation:
    pass


@dataclass
class Certificate:
    pass

