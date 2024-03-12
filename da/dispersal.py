from dataclasses import dataclass
from typing import List, Optional, Generator, Sequence

from py_ecc.bls import G2ProofOfPossession as bls_pop

from da.common import Certificate, NodeId, BLSPublickey
from da.encoder import EncodedData
from da.verifier import DABlob, Attestation


@dataclass
class DispersalSettings:
    nodes_ids: List[NodeId]
    nodes_pubkey: List[BLSPublickey]
    threshold: int


class Dispersal:
    def __init__(self, settings: DispersalSettings):
        self.settings = settings

    def _prepare_data(self, encoded_data: EncodedData) -> Generator[DABlob, None, None]:
        assert len(encoded_data.row_commitments) == len(self.settings.nodes_ids)
        assert len(encoded_data.row_proofs) == len(self.settings.nodes_ids)
        columns = encoded_data.extended_matrix.columns
        column_commitments = encoded_data.column_commitments
        row_commitments = encoded_data.row_commitments
        rows_proofs = encoded_data.row_proofs
        aggregated_column_commitment = encoded_data.aggregated_column_commitment
        aggregated_column_proofs = encoded_data.aggregated_column_proofs
        blobs_data = enumerate(zip(columns, column_commitments, rows_proofs, aggregated_column_proofs))
        for index, (column, column_commitment, row_proofs, column_proof) in blobs_data:
            blob = DABlob(
                index,
                column,
                column_commitment,
                aggregated_column_commitment,
                column_proof,
                row_commitments,
                row_proofs
            )
            yield blob

    def _send_and_await_response(self, node: NodeId, encoded_data: EncodedData) -> Optional[Attestation]:
        pass

    def _build_certificate(self, encoded_data: EncodedData, attestations: Sequence[Attestation]) -> Certificate:
        assert len(attestations) >= self.settings.threshold
        aggregated = bls_pop.Aggregate([attestation.signature for attestation in attestations])
        return Certificate(
            aggregated_signatures=aggregated,
            aggregated_column_commitment=encoded_data.aggregated_column_commitment,
            row_commitments=encoded_data.row_commitments
        )

    @staticmethod
    def _verify_attestation(public_key: BLSPublickey, attested_message: bytes, attestation: Attestation) -> bool:
        return bls_pop.Verify(public_key, attested_message, attestation.signature)

    def disperse(self, encoded_data: EncodedData) -> Optional[Certificate]:
        attestations = []

        for node, blob in zip(self.settings.nodes_ids, self._prepare_data(encoded_data)):
            if attestation := self._send_and_await_response(node, blob):
                if self._verify_attestation(attestation):
                    attestations.append(attestation)
            if len(attestations) >= self.settings.threshold:
                return self._build_certificate(encoded_data, attestations)
