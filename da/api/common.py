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

    def write(self, certificate, metadata):
        # TODO: Certificate indexing can fail.
        self.store.add(certificate, metadata)
        return

    def read(self, app_id, indexes) -> Optional[List[Optional[DABlob]]]:
        # Gather requested indexes for the app_id.
        return self.store.get_multiple(app_id, indexes)
