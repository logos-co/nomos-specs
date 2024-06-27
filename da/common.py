from dataclasses import dataclass
from hashlib import sha3_256
from itertools import chain, zip_longest, compress
from typing import List, Generator, Self, Sequence

from eth2spec.eip7594.mainnet import Bytes32, KZGCommitment as Commitment
from py_ecc.bls import G2ProofOfPossession


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


BLSPublicKey = bytes
BLSPrivateKey = int
BLSSignature = bytes


class Bitfield(List[bool]):
    pass


@dataclass
class Attestation:
    signature: BLSSignature


@dataclass
class Certificate:
    aggregated_signatures: BLSSignature
    signers: Bitfield
    aggregated_column_commitment: Commitment
    row_commitments: List[Commitment]

    def id(self) -> bytes:
        return build_attestation_message(self.aggregated_column_commitment, self.row_commitments)

    def verify(self, nodes_public_keys: List[BLSPublicKey]) -> bool:
        """
        List of nodes public keys should be a trusted list of verified proof of possession keys.
        Otherwise, we could fall under the Rogue Key Attack
        `assert all(bls_pop.PopVerify(pk, proof) for pk, proof in zip(node_public_keys, pops))`
        """
        # we sort them as the signers bitfield is sorted by the public keys as well
        signers_keys = list(compress(sorted(nodes_public_keys), self.signers))
        message = build_attestation_message(self.aggregated_column_commitment, self.row_commitments)
        return NomosDaG2ProofOfPossession.AggregateVerify(signers_keys, [message]*len(signers_keys), self.aggregated_signatures)


def build_attestation_message(aggregated_column_commitment: Commitment, row_commitments: Sequence[Commitment]) -> bytes:
    hasher = sha3_256()
    hasher.update(bytes(aggregated_column_commitment))
    for c in row_commitments:
        hasher.update(bytes(c))
    return hasher.digest()

class NomosDaG2ProofOfPossession(G2ProofOfPossession):
    # Domain specific tag for Nomos DA protocol
    DST = b"NOMOS_DA_AVAIL"
