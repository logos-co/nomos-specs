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

        self.app_id_store[metadata.app_id][metadata.index] = cert_id

    # Implements `get_multiple` method from BlobStore abstract class.
    def get_multiple(self, app_id, indexes) -> List[Optional[DABlob]]:
        return [
            self.blob_store.get(self.app_id_store[app_id].get(i), None) if self.app_id_store[app_id].get(i) else None for i in indexes
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

        api = DAApi(mock_store)

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

        api = DAApi(mock_store)

        api.write(cert_id, mock_meta)
        with self.assertRaises(ValueError):
            api.write(cert_id, mock_meta)

        blobs = api.read(app_id, [idx])

        self.assertEqual([expected_blob], blobs)

    def test_multiple_indexes_same_data(self):
        expected_blob = "hello"
        cert_id = b"11"*32
        app_id = 1
        idx1 = 1
        idx2 = 2
        mock_meta1 = Metadata(app_id, idx1)
        mock_meta2 = Metadata(app_id, idx2)

        mock_store = MockStore()
        mock_store.populate(expected_blob, cert_id)

        api = DAApi(mock_store)

        api.write(cert_id, mock_meta1)
        mock_store.populate(expected_blob, cert_id)
        api.write(cert_id, mock_meta2)

        blobs_idx1 = api.read(app_id, [idx1])
        blobs_idx2 = api.read(app_id, [idx2])

        self.assertEqual([expected_blob], blobs_idx1)
        self.assertEqual([expected_blob], blobs_idx2)
        self.assertEqual(mock_store.app_id_store[app_id][idx1], mock_store.app_id_store[app_id][idx2])

