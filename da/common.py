from dataclasses import dataclass
from hashlib import blake2b
from itertools import chain, zip_longest, compress
from typing import List, Generator, Self, Sequence

from eth2spec.eip7594.mainnet import Bytes32, KZGCommitment as Commitment
from eth2spec.eip7594.mainnet import BLSFieldElement
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


def build_blob_id(row_commitments: Sequence[Commitment]) -> BlobId:
    hasher = blake2b(digest_size=32)
    for c in row_commitments:
        hasher.update(bytes(c))
    return hasher.digest()


def derive_challenge(row_commitments: List[Commitment]) -> BLSFieldElement:
    """
    Derive a Fiat–Shamir challenge scalar h from the row commitments:
        h = BLAKE2b-31( DST || bytes(com1) || bytes(com2) || ... )
    """
    _DST = b"NOMOS_DA_V1"
    h = blake2b(digest_size=31)
    h.update(_DST)
    for com in row_commitments:
        h.update(bytes(com))
    digest31 = h.digest()  # 31 bytes
    # pad to 32 bytes for field element conversion
    padded = digest31 + b'\x00'
    return BLSFieldElement.from_bytes(padded)


class NomosDaG2ProofOfPossession(G2ProofOfPossession):
    # Domain specific tag for Nomos DA protocol
    DST = b"NOMOS_DA_AVAIL"
