from dataclasses import dataclass
from typing import List, Generator

from eth2spec.eip7594.mainnet import Bytes32


class NodeId(Bytes32):
    pass

class Chunk(Bytes32):
    pass


class Column(bytes):
    pass


class Row(bytes):
    pass


class ChunksMatrix(List[Row]):
    @property
    def columns(self) -> Generator[List[Chunk], None, None]:
        yield from map(list, zip(*self))




@dataclass
class Attestation:
    pass


@dataclass
class Certificate:
    pass

