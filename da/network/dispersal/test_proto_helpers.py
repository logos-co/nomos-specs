import dispersal_pb2
import proto
from unittest import TestCase

class TestMessageSerialization(TestCase):

    def test_dispersal_req_msg(self):
        blob_id = b"dummy_blob_id"
        data = b"dummy_data"
        packed_message = proto.new_dispersal_req_msg(blob_id, data)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('dispersal_req'))
        self.assertEqual(message.dispersal_req.blob.blob_id, blob_id)
        self.assertEqual(message.dispersal_req.blob.data, data)

    def test_dispersal_res_success_msg(self):
        blob_id = b"dummy_blob_id"
        packed_message = proto.new_dispersal_res_success_msg(blob_id)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('dispersal_res'))
        self.assertEqual(message.dispersal_res.blob_id, blob_id)

    def test_dispersal_res_chunk_size_error_msg(self):
        blob_id = b"dummy_blob_id"
        description = "Chunk size error"
        packed_message = proto.new_dispersal_res_chunk_size_error_msg(blob_id, description)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('dispersal_res'))
        self.assertEqual(message.dispersal_res.err.blob_id, blob_id)
        self.assertEqual(message.dispersal_res.err.err_type, dispersal_pb2.DispersalErr.CHUNK_SIZE)
        self.assertEqual(message.dispersal_res.err.err_description, description)

    def test_dispersal_res_verification_error_msg(self):
        blob_id = b"dummy_blob_id"
        description = "Verification error"
        packed_message = proto.new_dispersal_res_verification_error_msg(blob_id, description)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('dispersal_res'))
        self.assertEqual(message.dispersal_res.err.blob_id, blob_id)
        self.assertEqual(message.dispersal_res.err.err_type, dispersal_pb2.DispersalErr.VERIFICATION)
        self.assertEqual(message.dispersal_res.err.err_description, description)

    def test_sample_req_msg(self):
        blob_id = b"dummy_blob_id"
        packed_message = proto.new_sample_req_msg(blob_id)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('sample_req'))
        self.assertEqual(message.sample_req.blob_id, blob_id)

    def test_sample_res_success_msg(self):
        blob_id = b"dummy_blob_id"
        data = b"dummy_data"
        packed_message = proto.new_sample_res_success_msg(blob_id, data)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('sample_res'))
        self.assertEqual(message.sample_res.blob.blob_id, blob_id)
        self.assertEqual(message.sample_res.blob.data, data)

    def test_sample_res_not_found_error_msg(self):
        blob_id = b"dummy_blob_id"
        description = "Blob not found"
        packed_message = proto.new_sample_res_not_found_error_msg(blob_id, description)
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('sample_res'))
        self.assertEqual(message.sample_res.err.blob_id, blob_id)
        self.assertEqual(message.sample_res.err.err_type, dispersal_pb2.SampleErr.NOT_FOUND)
        self.assertEqual(message.sample_res.err.err_description, description)

    def test_session_req_close_msg(self):
        reason = dispersal_pb2.CloseMsg.GRACEFUL_SHUTDOWN
        packed_message = proto.new_session_req_graceful_shutdown_msg()
        message = proto.unpack_from_bytes(packed_message)
        self.assertTrue(message.HasField('session_req'))
        self.assertTrue(message.session_req.HasField('close_msg'))
        self.assertEqual(message.session_req.close_msg.reason, reason)
