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

    def _send_and_await_response(self, node: NodeId, blob: DABlob) -> bool:
        pass

    def disperse(self, encoded_data: EncodedData):
        attestations = []
        blob_data = zip(
            self.settings.nodes_ids,
            self._prepare_data(encoded_data)
        )
        for i, node, blob in blob_data:
            self._send_and_await_response(node, blob)

