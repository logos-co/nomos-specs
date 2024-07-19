from itertools import count

import dispersal.dispersal_pb2 as dispersal_pb2

MAX_MSG_LEN_BYTES = 2


def pack_message(message):
    # SerializeToString method returns an instance of bytes.
    data = message.SerializeToString()
    length_prefix = len(data).to_bytes(MAX_MSG_LEN_BYTES, byteorder="big")
    return length_prefix + data


async def unpack_from_reader(reader):
    length_prefix = await reader.readexactly(MAX_MSG_LEN_BYTES)
    data_length = int.from_bytes(length_prefix, byteorder="big")
    data = await reader.readexactly(data_length)
    return parse(data)


def unpack_from_bytes(data):
    length_prefix = data[:MAX_MSG_LEN_BYTES]
    data_length = int.from_bytes(length_prefix, byteorder="big")
    return parse(data[MAX_MSG_LEN_BYTES : MAX_MSG_LEN_BYTES + data_length])


def parse(data):
    message = dispersal_pb2.DispersalMessage()
    message.ParseFromString(data)
    return message


# DISPERSAL


def new_dispersal_req_msg(blob_id, data):
    blob = dispersal_pb2.Blob(blob_id=blob_id, data=data)
    dispersal_req = dispersal_pb2.DispersalReq(blob=blob)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_req=dispersal_req)
    return pack_message(dispersal_message)


def new_dispersal_res_success_msg(blob_id):
    dispersal_res = dispersal_pb2.DispersalRes(blob_id=blob_id)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)


def new_dispersal_res_chunk_size_error_msg(blob_id, description):
    dispersal_err = dispersal_pb2.DispersalErr(
        blob_id=blob_id,
        err_type=dispersal_pb2.DispersalErr.CHUNK_SIZE,
        err_description=description,
    )
    dispersal_res = dispersal_pb2.DispersalRes(err=dispersal_err)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)


def new_dispersal_res_verification_error_msg(blob_id, description):
    dispersal_err = dispersal_pb2.DispersalErr(
        blob_id=blob_id,
        err_type=dispersal_pb2.DispersalErr.VERIFICATION,
        err_description=description,
    )
    dispersal_res = dispersal_pb2.DispersalRes(err=dispersal_err)
    dispersal_message = dispersal_pb2.DispersalMessage(dispersal_res=dispersal_res)
    return pack_message(dispersal_message)


# SAMPLING


def new_sample_req_msg(blob_id):
    sample_req = dispersal_pb2.SampleReq(blob_id=blob_id)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_req=sample_req)
    return pack_message(dispersal_message)


def new_sample_res_success_msg(blob_id, data):
    blob = dispersal_pb2.Blob(blob_id=blob_id, data=data)
    sample_res = dispersal_pb2.SampleRes(blob=blob)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)


def new_sample_res_not_found_error_msg(blob_id, description):
    sample_err = dispersal_pb2.SampleErr(
        blob_id=blob_id,
        err_type=dispersal_pb2.SampleErr.NOT_FOUND,
        err_description=description,
    )
    sample_res = dispersal_pb2.SampleRes(err=sample_err)
    dispersal_message = dispersal_pb2.DispersalMessage(sample_res=sample_res)
    return pack_message(dispersal_message)


# SESSION CONTROL


def new_close_msg(reason):
    close_msg = dispersal_pb2.CloseMsg(reason=reason)
    return close_msg


def new_session_req_close_msg(reason):
    close_msg = new_close_msg(reason)
    session_req = dispersal_pb2.SessionReq(close_msg=close_msg)
    dispersal_message = dispersal_pb2.DispersalMessage(session_req=session_req)
    return dispersal_message


def new_session_req_graceful_shutdown_msg():
    message = new_session_req_close_msg(dispersal_pb2.CloseMsg.GRACEFUL_SHUTDOWN)
    return pack_message(message)


def new_session_req_subnet_change_msg():
    message = new_session_req_close_msg(dispersal_pb2.CloseMsg.SUBNET_CHANGE)
    return pack_message(message)


def new_session_req_subnet_sample_fail_msg():
    message = new_session_req_close_msg(dispersal_pb2.CloseMsg.SUBNET_SAMPLE_FAIL)
    return pack_message(message)
