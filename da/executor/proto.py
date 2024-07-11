import dispersal_pb2
from itertools import count

MAX_MSG_LEN_BYTES = 2

def pack_message(message):
    # SerializeToString method returns an instance of bytes.
    data = message.SerializeToString()
    length_prefix = len(data).to_bytes(MAX_MSG_LEN_BYTES, byteorder='big')
    return length_prefix + data

def unpack_message(data):
    message = dispersal_pb2.DispersalMessage()
    message.ParseFromString(data)
    return message

def new_dispersal_req_msg(blob_id, data):
    blob = dispersal_pb2.Blob(blob_id=blob_id, data=data)
    dispersal_req = dispersal_pb2.DispersalReq(blob=blob)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_req=dispersal_req)
    return pack_message(dispersal_message)

def new_dispersal_res_success_msg(blob_id):
    blob_id_msg = dispersal_pb2.BlobId(blob_id=blob_id)
    dispersal_res = dispersal_pb2.DispersalRes(blob_id=blob_id_msg)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)

def new_dispersal_res_chunk_size_error_msg(description):
    error = dispersal_pb2.Error(description=description)
    dispersal_err = dispersal_pb2.DispersalErr(chunk_size_err=error)
    dispersal_res = dispersal_pb2.DispersalRes(err=dispersal_err)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)

def new_dispersal_res_verification_error_msg(description):
    error = dispersal_pb2.Error(description=description)
    dispersal_err = dispersal_pb2.DispersalErr(verification_err=error)
    dispersal_res = dispersal_pb2.DispersalRes(err=dispersal_err)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)

def new_sample_req_msg(blob_id):
    blob_id_msg = dispersal_pb2.BlobId(blob_id=blob_id)
    sample_req = dispersal_pb2.SampleReq(blob_id=blob_id_msg)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_req=sample_req)
    return pack_message(dispersal_message)

def new_sample_res_success_msg(blob_id, data):
    blob = dispersal_pb2.Blob(blob_id=blob_id, data=data)
    sample_res = dispersal_pb2.SampleRes(blob=blob)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)

def new_sample_res_not_found_error_msg(description):
    error = dispersal_pb2.Error(description=description)
    sample_err = dispersal_pb2.SampleErr(not_found=error)
    sample_res = dispersal_pb2.SampleRes(err=sample_err)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)

