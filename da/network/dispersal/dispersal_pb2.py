# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: dispersal.proto
# Protobuf Python Version: 5.27.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    1,
    '',
    'dispersal.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x0f\x64ispersal.proto\x12\x15nomos.da.dispersal.v1\"%\n\x04\x42lob\x12\x0f\n\x07\x62lob_id\x18\x01 \x01(\x0c\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\x0c\"\xb6\x01\n\x0c\x44ispersalErr\x12\x0f\n\x07\x62lob_id\x18\x01 \x01(\x0c\x12\x46\n\x08\x65rr_type\x18\x02 \x01(\x0e\x32\x34.nomos.da.dispersal.v1.DispersalErr.DispersalErrType\x12\x17\n\x0f\x65rr_description\x18\x03 \x01(\t\"4\n\x10\x44ispersalErrType\x12\x0e\n\nCHUNK_SIZE\x10\x00\x12\x10\n\x0cVERIFICATION\x10\x01\"9\n\x0c\x44ispersalReq\x12)\n\x04\x62lob\x18\x01 \x01(\x0b\x32\x1b.nomos.da.dispersal.v1.Blob\"e\n\x0c\x44ispersalRes\x12\x11\n\x07\x62lob_id\x18\x01 \x01(\x0cH\x00\x12\x32\n\x03\x65rr\x18\x02 \x01(\x0b\x32#.nomos.da.dispersal.v1.DispersalErrH\x00\x42\x0e\n\x0cmessage_type\"\x97\x01\n\tSampleErr\x12\x0f\n\x07\x62lob_id\x18\x01 \x01(\x0c\x12@\n\x08\x65rr_type\x18\x02 \x01(\x0e\x32..nomos.da.dispersal.v1.SampleErr.SampleErrType\x12\x17\n\x0f\x65rr_description\x18\x03 \x01(\t\"\x1e\n\rSampleErrType\x12\r\n\tNOT_FOUND\x10\x00\"\x1c\n\tSampleReq\x12\x0f\n\x07\x62lob_id\x18\x01 \x01(\x0c\"y\n\tSampleRes\x12+\n\x04\x62lob\x18\x01 \x01(\x0b\x32\x1b.nomos.da.dispersal.v1.BlobH\x00\x12/\n\x03\x65rr\x18\x02 \x01(\x0b\x32 .nomos.da.dispersal.v1.SampleErrH\x00\x42\x0e\n\x0cmessage_type\"\x98\x01\n\x08\x43loseMsg\x12;\n\x06reason\x18\x01 \x01(\x0e\x32+.nomos.da.dispersal.v1.CloseMsg.CloseReason\"O\n\x0b\x43loseReason\x12\x15\n\x11GRACEFUL_SHUTDOWN\x10\x00\x12\x11\n\rSUBNET_CHANGE\x10\x01\x12\x16\n\x12SUBNET_SAMPLE_FAIL\x10\x02\"R\n\nSessionReq\x12\x34\n\tclose_msg\x18\x01 \x01(\x0b\x32\x1f.nomos.da.dispersal.v1.CloseMsgH\x00\x42\x0e\n\x0cmessage_type\"\xc8\x02\n\x10\x44ispersalMessage\x12<\n\rdispersal_req\x18\x01 \x01(\x0b\x32#.nomos.da.dispersal.v1.DispersalReqH\x00\x12<\n\rdispersal_res\x18\x02 \x01(\x0b\x32#.nomos.da.dispersal.v1.DispersalResH\x00\x12\x36\n\nsample_req\x18\x03 \x01(\x0b\x32 .nomos.da.dispersal.v1.SampleReqH\x00\x12\x36\n\nsample_res\x18\x04 \x01(\x0b\x32 .nomos.da.dispersal.v1.SampleResH\x00\x12\x38\n\x0bsession_req\x18\x05 \x01(\x0b\x32!.nomos.da.dispersal.v1.SessionReqH\x00\x42\x0e\n\x0cmessage_typeb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'dispersal_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_BLOB']._serialized_start=42
  _globals['_BLOB']._serialized_end=79
  _globals['_DISPERSALERR']._serialized_start=82
  _globals['_DISPERSALERR']._serialized_end=264
  _globals['_DISPERSALERR_DISPERSALERRTYPE']._serialized_start=212
  _globals['_DISPERSALERR_DISPERSALERRTYPE']._serialized_end=264
  _globals['_DISPERSALREQ']._serialized_start=266
  _globals['_DISPERSALREQ']._serialized_end=323
  _globals['_DISPERSALRES']._serialized_start=325
  _globals['_DISPERSALRES']._serialized_end=426
  _globals['_SAMPLEERR']._serialized_start=429
  _globals['_SAMPLEERR']._serialized_end=580
  _globals['_SAMPLEERR_SAMPLEERRTYPE']._serialized_start=550
  _globals['_SAMPLEERR_SAMPLEERRTYPE']._serialized_end=580
  _globals['_SAMPLEREQ']._serialized_start=582
  _globals['_SAMPLEREQ']._serialized_end=610
  _globals['_SAMPLERES']._serialized_start=612
  _globals['_SAMPLERES']._serialized_end=733
  _globals['_CLOSEMSG']._serialized_start=736
  _globals['_CLOSEMSG']._serialized_end=888
  _globals['_CLOSEMSG_CLOSEREASON']._serialized_start=809
  _globals['_CLOSEMSG_CLOSEREASON']._serialized_end=888
  _globals['_SESSIONREQ']._serialized_start=890
  _globals['_SESSIONREQ']._serialized_end=972
  _globals['_DISPERSALMESSAGE']._serialized_start=975
  _globals['_DISPERSALMESSAGE']._serialized_end=1303
# @@protoc_insertion_point(module_scope)
