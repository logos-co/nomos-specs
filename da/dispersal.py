from dataclasses import dataclass
from typing import List, Generator

from da.common import Certificate, NodeId, BLSPublicKey, Bitfield, build_blob_id, NomosDaG2ProofOfPossession as bls_pop
from da.encoder import EncodedData
from da.verifier import DAShare


@dataclass
class DispersalSettings:
    nodes_ids: List[NodeId]
    threshold: int


class Dispersal:
    def __init__(self, settings: DispersalSettings):
        self.settings = settings
        # sort over public keys
        self.settings.nodes_ids.sort()

    def _prepare_data(self, encoded_data: EncodedData) -> Generator[DAShare, None, None]:
        columns = encoded_data.extended_matrix.columns
        row_commitments = encoded_data.row_commitments
        column_proofs = encoded_data.combined_column_proofs
        blobs_data = zip(columns, column_proofs)
        for column_idx, (column, proof) in enumerate(blobs_data):
            blob = DAShare(
                Column(column),
                column_idx,
                proof,
                row_commitments
            )
            yield blob

    def _send_and_await_response(self, node: NodeId, blob: DAShare) -> bool:
        pass

    def _build_certificate(
            self,
            encoded_data: EncodedData,
            attestations: Sequence[Attestation],
            signers: Bitfield
    ) -> Certificate:
        assert len(attestations) >= self.settings.threshold
        assert len(attestations) == signers.count(True)
        aggregated = bls_pop.Aggregate([attestation.signature for attestation in attestations])
        return Certificate(
            aggregated_signatures=aggregated,
            signers=signers,
            aggregated_column_commitment=encoded_data.aggregated_column_commitment,
            row_commitments=encoded_data.row_commitments
        )

    @staticmethod
    def _verify_attestation(public_key: BLSPublicKey, attested_message: bytes, attestation: Attestation) -> bool:
        return bls_pop.Verify(public_key, attested_message, attestation.signature)

    @staticmethod
    def _build_attestation_message(encoded_data: EncodedData) -> bytes:
        return build_blob_id(encoded_data.aggregated_column_commitment, encoded_data.row_commitments)

    def disperse(self, encoded_data: EncodedData) -> Optional[Certificate]:
        attestations = []
        attested_message = self._build_attestation_message(encoded_data)
        signed = Bitfield(False for _ in range(len(self.settings.nodes_ids)))
        blob_data = zip(
            self.settings.nodes_ids,
            self._prepare_data(encoded_data)
        )
        for node, blob in blob_data:
            self._send_and_await_response(node, blob)

