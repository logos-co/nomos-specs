from dataclasses import dataclass
from hashlib import sha3_256
from typing import List, Optional, Generator, Sequence

from da.common import Certificate, NodeId, BLSPublicKey, Bitfield, build_attestation_message, NomosDaG2ProofOfPossession as bls_pop
from da.encoder import EncodedData
from da.verifier import DABlob, Attestation


@dataclass
class DispersalSettings:
    nodes_ids: List[NodeId]
    nodes_pubkey: List[BLSPublicKey]
    threshold: int


class Dispersal:
    def __init__(self, settings: DispersalSettings):
        self.settings = settings
        # sort over public keys
        self.settings.nodes_ids, self.settings.nodes_pubkey = zip(
            *sorted(zip(self.settings.nodes_ids, self.settings.nodes_pubkey), key=lambda x: x[1])
        )

    def _prepare_data(self, encoded_data: EncodedData) -> Generator[DABlob, None, None]:
        assert len(encoded_data.column_commitments) == len(self.settings.nodes_ids)
        assert len(encoded_data.aggregated_column_proofs) == len(self.settings.nodes_ids)
        columns = encoded_data.extended_matrix.columns
        column_commitments = encoded_data.column_commitments
        row_commitments = encoded_data.row_commitments
        rows_proofs = encoded_data.row_proofs
        aggregated_column_commitment = encoded_data.aggregated_column_commitment
        aggregated_column_proofs = encoded_data.aggregated_column_proofs
        blobs_data = zip(columns, column_commitments, zip(*rows_proofs), aggregated_column_proofs)
        for (column, column_commitment, row_proofs, column_proof) in blobs_data:
            blob = DABlob(
                column,
                column_commitment,
                aggregated_column_commitment,
                column_proof,
                row_commitments,
                row_proofs
            )
            yield blob

    def _send_and_await_response(self, node: NodeId, blob: DABlob) -> Optional[Attestation]:
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
        return build_attestation_message(encoded_data.aggregated_column_commitment, encoded_data.row_commitments)

    def disperse(self, encoded_data: EncodedData) -> Optional[Certificate]:
        attestations = []
        attested_message = self._build_attestation_message(encoded_data)
        signed = Bitfield(False for _ in range(len(self.settings.nodes_ids)))
        blob_data = zip(
            range(len(self.settings.nodes_ids)),
            self.settings.nodes_ids,
            self.settings.nodes_pubkey,
            self._prepare_data(encoded_data)
        )
        for i, node, pk, blob in blob_data:
            if attestation := self._send_and_await_response(node, blob):
                if self._verify_attestation(pk, attested_message, attestation):
                    # mark as received
                    signed[i] = True
                    attestations.append(attestation)
            if len(attestations) >= self.settings.threshold:
                return self._build_certificate(encoded_data, attestations, signed)
