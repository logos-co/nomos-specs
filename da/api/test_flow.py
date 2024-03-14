from unittest import TestCase
from collections import defaultdict

from da.api.common import *

@dataclass
class MockCertificate:
    cert_id: int

class MockStore(BlobStore):
    def __init__(self):
        self.blob_store = {}
        self.app_id_store = defaultdict(dict)

    def populate(self, blob, cert_id: bytes):
        self.blob_store[cert_id] = blob

    # Implements `add` method from BlobStore abstract class.
    def add(self, cert_id: bytes, metadata: Metadata):
        if metadata.index in self.app_id_store[metadata.app_id]:
            raise ValueError("index already written")

        blob = self.blob_store.pop(cert_id)
        self.app_id_store[metadata.app_id][metadata.index] = blob 

    # Implements `get_multiple` method from BlobStore abstract class.
    def get_multiple(self, app_id, indexes) -> List[Optional[DABlob]]:
        return [
                self.app_id_store[app_id].get(i) for i in indexes
        ]


class TestFlow(TestCase):
    def test_api_write_read(self):
        expected_blob = "hello"
        cert_id = b"11"*32
        app_id = 1
        idx = 1
        mock_meta = Metadata(1, 1)

        mock_store = MockStore()
        mock_store.populate(expected_blob, cert_id)

        api = Api(mock_store)

        api.write(cert_id, mock_meta)
        blobs = api.read(app_id, [idx])

        self.assertEqual([expected_blob], blobs)

    def test_same_index(self):
        expected_blob = "hello"
        cert_id = b"11"*32
        app_id = 1
        idx = 1
        mock_meta = Metadata(1, 1)

        mock_store = MockStore()
        mock_store.populate(expected_blob, cert_id)

        api = Api(mock_store)

        api.write(cert_id, mock_meta)
        with self.assertRaises(ValueError):
            api.write(cert_id, mock_meta)

        blobs = api.read(app_id, [idx])

        self.assertEqual([expected_blob], blobs)

