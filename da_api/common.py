from dataclasses import dataclass

from da.verifier import DABlob
from da.common import Certificate, NodeId

@dataclass
class Metadata:
    index: int
    app_id: int

@dataclass
class DABlobWMetadata:
    blob: DABlob
    metadata: Metadata

@dataclass
class CertificateWMetadata:
    certificate: Certificate
    metadata: Metadata
