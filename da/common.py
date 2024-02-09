from dataclasses import dataclass
from typing import List

from eth2spec.eip7594.mainnet import Bytes32


class Chunk(Bytes32):
    pass


class Column(List[Chunk]):
    pass


class Row(List[Chunk]):
    pass


class ChunksMatrix(List[Row]):
    pass


@dataclass
class Attestation:
    pass


@dataclass
class Certificate:
    pass

