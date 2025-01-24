from dataclasses import dataclass
from typing import List, Generator

from da.common import NodeId
from da.encoder import EncodedData
from da.verifier import DABlob


@dataclass
class DispersalSettings:
    nodes_ids: List[NodeId]
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

    def _send_and_await_response(self, node: NodeId, blob: DABlob) -> bool:
        pass

    def disperse(self, encoded_data: EncodedData):
        attestations = []
        blob_data = zip(
            range(len(self.settings.nodes_ids)),
            self.settings.nodes_ids,
            self._prepare_data(encoded_data)
        )
        for i, node, blob in blob_data:
            self._send_and_await_response(node, blob)

