from dataclasses import dataclass
from typing import List
from eth2spec.eip7594.mainnet import KZGCommitment as Commitment, KZGProof as Proof


@dataclass
class DABlob:
    # this should be removed, but for now it shows the purpose
    index: int
    column: bytearray
    column_commitment: Commitment
    aggregated_column_commitment: Commitment
    aggregated_column_proof: Proof
    rows_commitments: List[Commitment]
    rows_proofs: List[Proof]
