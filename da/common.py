from dataclasses import dataclass
from hashlib import sha3_256
from itertools import chain, zip_longest, compress
from typing import List, Generator, Self, Sequence

from eth2spec.eip7594.mainnet import Bytes32, KZGCommitment as Commitment
from py_ecc.bls import G2ProofOfPossession


type BlobId = bytes

class NodeId(Bytes32):
    pass


class Chunk(bytes):
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



class Bitfield(List[bool]):
    pass


def build_blob_id(aggregated_column_commitment: Commitment, row_commitments: Sequence[Commitment]) -> BlobId:
    hasher = sha3_256()
    hasher.update(bytes(aggregated_column_commitment))
    for c in row_commitments:
        hasher.update(bytes(c))
    return hasher.digest()

class NomosDaG2ProofOfPossession(G2ProofOfPossession):
    # Domain specific tag for Nomos DA protocol
    DST = b"NOMOS_DA_AVAIL"
