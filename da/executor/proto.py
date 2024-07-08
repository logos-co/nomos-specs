import struct
from itertools import count

DISPERSAL_PUT = 0x01
DISPERSAL_OK = 0x02
SAMPLE_PUT = 0x03
SAMPLE_OK = 0x04

HEADER_SIZE = 9
HEADER_FORMAT = "!B I I"

DISPERSAL_HASH_COL_SIZE = 6
# First 4 bytes for the hash and the next 2 bytes for the column index.
DISPERSAL_HASH_COL_FORMAT = "!I H"

msg_id_counter = count(start=1)

def pack_header(msg_type, msg_id, data):
    encoded_data = data.encode()
    data_length = len(encoded_data)
    header = struct.pack(HEADER_FORMAT, msg_type, msg_id, data_length)
    return header + encoded_data

def unpack_header(data):
    if len(data) < HEADER_SIZE:
        return None, None, None, None
    msg_type, msg_id, data_length = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    return msg_type, msg_id, data_length

def new_dispersal_put_msg(data):
    msg_id = next(msg_id_counter)
    return pack_header(DISPERSAL_PUT, msg_id, data)

def new_dispersal_ok_msg(msg_id):
    return pack_header(DISPERSAL_OK, msg_id, "")

def new_sample_put_msg(data):
    msg_id = next(msg_id_counter)
    return pack_header(SAMPLE_PUT, msg_id, data)

def new_sample_ok_msg(msg_id, response_data):
    return pack_header(SAMPLE_OK, msg_id, response_data)

def parse_dispersal_data(data):
    if len(data) >= DISPERSAL_HASH_COL_SIZE:
        hash_value, col_index = struct.unpack(DISPERSAL_HASH_COL_FORMAT, data[:DISPERSAL_HASH_COL_SIZE])
        remaining_data = data[DISPERSAL_HASH_COL_SIZE:]
        return hash_value, col_index, remaining_data
    else:
        raise ValueError("Data is too short to unpack hash and col.")
