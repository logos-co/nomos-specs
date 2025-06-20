from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Sequence

from da.common import BlobId
from da.verifier import DABlob


@dataclass
class Metadata:
    # app identifier
    app_id: bytes
    # index of VID certificate blob
    index: int


@dataclass
class BlobMetadata:
    # da blob_id id
    blob_id: BlobId
    # application + index information
    metadata: Metadata


class BlobStore(ABC):
    @abstractmethod
    def add(self, id: BlobId, metadata: Metadata):
        """
        Raises: ValueError if there is already a registered certificate fot the given metadata
        """
        pass

    @abstractmethod
    def get_multiple(self, app_id: bytes, indexes: Sequence[int]) -> List[Optional[DAShare]]:
        pass


class DAApi:
    def __init__(self, bs: BlobStore):
        self.store = bs

    def write(self, id: BlobId, metadata: Metadata):
        """
        Write method should be used by a service that is able to retrieve verified certificates
        from the latest Block. Once a certificate is retrieved, api creates a relation between
        the blob of an original data, certificate and index for the app_id of the certificate.
        Raises: ValueError if there is already a registered certificate for a given metadata
        """
        self.store.add(id, metadata)

    def read(self, app_id, indexes) -> List[Optional[DAShare]]:
        """
        Read method should accept only `app_id` and a list of indexes. The returned list of
        blobs should be ordered in the same sequence as `indexes` in a request.
        If node does not have the blob for some indexes, then it should add None object as an
        item.
        """
        return self.store.get_multiple(app_id, indexes)
