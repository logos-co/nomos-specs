from dataclasses import dataclass
from typing import TypeAlias, List

from da.verifier import Attestation, DABlob
from da.common import Certificate, NodeId

Id: TypeAlias = bytes

@dataclass
class Metadata:
    index: int
    app_id: Id

@dataclass
class AttestationMessage:
    attestation: Attestation
    metadata: Metadata
    blob_id: Id # TODO: might be included in the Attestation itself.

@dataclass
class DABlobMessage:
    blob: DABlob
    metadata: Metadata

@dataclass
class CertificateMessage:
    certificate: Certificate
    metadata: Metadata

@dataclass
class VID:
    certificate_hash: Id
    metadata: Metadata

class BlockMessage:
    block_id: Id
    vids: List[VID]

DaApiMessage = DABlobMessage | AttestationMessage | CertificateMessage | BlockMessage

def data_hash(data: bytearray):
    # TODO: migth be unnecessary or moved to common.
    pass
