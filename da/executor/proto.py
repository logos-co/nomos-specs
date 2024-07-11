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
    dispersal_req = dispersal_pb2.DispersalReq(blob_id=blob_id, data=data)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_req=dispersal_req)
    return pack_message(dispersal_message)

def new_dispersal_res_msg(blob_id):
    dispersal_res = dispersal_pb2.DispersalRes(blob_id=blob_id)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)

def new_sample_req_msg(blob_id):
    sample_req = dispersal_pb2.SampleReq(blob_id=blob_id)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_req=sample_req)
    return pack_message(dispersal_message)

def new_sample_res_msg(blob_id, data):
    sample_res = dispersal_pb2.SampleRes(blob_id=blob_id, data=data)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)
