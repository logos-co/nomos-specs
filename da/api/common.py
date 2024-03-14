from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List

from da.verifier import DABlob

@dataclass
class Metadata:
    index: int
    app_id: int 

class BlobStore(ABC):
    @abstractmethod
    def add(certificate, metadata):
        pass

    @abstractmethod
    def get_multiple(app_id, indexes) -> List[DABlob]:
        pass

class Api:
    def __init__(self, bs: BlobStore):
        self.store = bs

    """
    Write method should be used by a service that is able to retrieve verified certificates
    from the latest Block. Once a certificate is retrieved, api creates a relation between
    the blob of an original data, certificate and index for the app_id of the certificate.
    """
    def write(self, certificate, metadata):
        self.store.add(certificate, metadata)
        return

    """
    Read method should accept only `app_id` and a list of indexes. The returned list of
    blobs should be ordered in the same sequence as `indexes` in a request.
    If node does not have the blob for some indexes, then it should add None object as an
    item.
    """
    def read(self, app_id, indexes) -> Optional[List[Optional[DABlob]]]:
        return self.store.get_multiple(app_id, indexes)
