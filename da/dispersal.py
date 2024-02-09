from typing import List, Optional, Generator

from da.common import Certificate
from da.encoder import EncodedData
from da.verifier import DABlob, Attestation
from mixnet.node import NodeId


class Dispersal:
    def __init__(self, nodes: List[NodeId], threshold: int):
        self.nodes = nodes
        self.threshold = threshold

    def _prepare_data(self, encoded_data: EncodedData) -> Generator[DABlob, None, None]:
        assert len(encoded_data.row_commitments) == len(self.nodes)
        assert len(encoded_data.row_proofs) == len(self.nodes)
        columns = encoded_data.columns
        column_commitments = encoded_data.column_commitments
        row_commitments = encoded_data.row_commitments
        rows_proofs = encoded_data.row_proofs
        aggregated_column_commitment = encoded_data.aggregated_column_commitment
        aggregated_column_proof = encoded_data.aggregated_column_proof
        for index, (column, column_commitment, row_proofs) in enumerate(zip(columns, column_commitments, rows_proofs)):
            blob = DABlob(
                index,
                column,
                column_commitment,
                aggregated_column_commitment,
                aggregated_column_proof,
                row_commitments,
                row_proofs
            )
            yield blob

    def _send_and_await_response(self, node, encoded_data: EncodedData) -> Optional[Attestation]:
        pass

    def _build_certificate(self, attestations: List[Attestation]):
        pass

    def _verify_attestation(self, attestation: Attestation) -> bool:
        pass

    def disperse(self, encoded_data: EncodedData) -> Optional[Certificate]:
        attestations = []
        for node, blob in zip(self.nodes, self._prepare_data(encoded_data)):
            if attestation := self._send_and_await_response(node, blob):
                if self._verify_attestation(attestation):
                    attestations.append(attestation)
            if len(attestations) >= self.threshold:
                return self._build_certificate(attestations)
