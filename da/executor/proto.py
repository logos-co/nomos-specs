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

def new_dispersal_res_msg(blob_id=None, error_type=None, error_description=None):
    if blob_id is not None:
        blob_id_msg = dispersal_pb2.BlobId(blob_id=blob_id)
        dispersal_res = dispersal_pb2.DispersalRes(blob_id=blob_id_msg)
    elif error_type is not None and error_description is not None:
        error = dispersal_pb2.Error(description=error_description)
        dispersal_err = dispersal_pb2.DispersalErr()
        setattr(dispersal_err, error_type, error)
        dispersal_res = dispersal_pb2.DispersalRes(err=dispersal_err)
    else:
        raise ValueError("Either blob_id or error_type and error_description must be provided")
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)

def new_sample_req_msg(blob_id):
    blob_id_msg = dispersal_pb2.BlobId(blob_id=blob_id)
    sample_req = dispersal_pb2.SampleReq(blob_id=blob_id_msg)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_req=sample_req)
    return pack_message(dispersal_message)

def new_sample_res_msg(blob_id=None, data=None, error_description=None):
    if blob_id is not None and data is not None:
        blob = dispersal_pb2.Blob(blob_id=blob_id, data=data)
        sample_res = dispersal_pb2.SampleRes(blob=blob)
    elif error_description is not None:
        error = dispersal_pb2.Error(description=error_description)
        sample_err = dispersal_pb2.SampleErr(not_found=error)
        sample_res = dispersal_pb2.SampleRes(err=sample_err)
    else:
        raise ValueError("Either blob_id and data or error_description must be provided")
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)

