# Zone Executor to Nomos DA Communication

Protocol for communication between the Zone Executor and Nomos DA using Protocol Buffers (protobuf).

## Overview

The protocol defines messages used to request and respond to data dispersal, sampling operations, and session control within the Nomos DA system. The communication involves the exchange of blobs (binary large objects) and error handling for various operations.

## Messages

### Blob
- **Blob**: Represents the binary data to be dispersed.
  - `bytes blob_id`: Unique identifier for the blob.
  - `bytes data`: The binary data of the blob.

### Error Handling
- **DispersalErr**: Represents errors related to dispersal operations.
  - `bytes blob_id`: Unique identifier of the blob related to the error.
  - `enum DispersalErrType`: Enumeration of dispersal error types.
    - `CHUNK_SIZE`: Error due to incorrect chunk size.
    - `VERIFICATION`: Error due to verification failure.
  - `string err_description`: Description of the error.

- **SampleErr**: Represents errors related to sample operations.
  - `bytes blob_id`: Unique identifier of the blob related to the error.
  - `enum SampleErrType`: Enumeration of sample error types.
    - `NOT_FOUND`: Error when a blob is not found.
  - `string err_description`: Description of the error.

### Dispersal
- **DispersalReq**: Request message for dispersing a blob.
  - `Blob blob`: The blob to be dispersed.

- **DispersalRes**: Response message for a dispersal request.
  - `oneof message_type`: Contains either a success response or an error.
    - `bytes blob_id`: Unique identifier of the dispersed blob.
    - `DispersalErr err`: Error occurred during dispersal.

### Sample
- **SampleReq**: Request message for sampling a blob.
  - `bytes blob_id`: Unique identifier of the blob to be sampled.

- **SampleRes**: Response message for a sample request.
  - `oneof message_type`: Contains either a success response or an error.
    - `Blob blob`: The sampled blob.
    - `SampleErr err`: Error occurred during sampling.

### Session Control
- **CloseMsg**: Message to close a session with a reason.
  - `enum CloseReason`: Enumeration of close reasons.
    - `GRACEFUL_SHUTDOWN`: Graceful shutdown of the session.
    - `SUBNET_CHANGE`: Change in the subnet.
    - `SUBNET_SAMPLE_FAIL`: Subnet sample failure.
  - `CloseReason reason`: Reason for closing the session.

- **SessionReq**: Request message for session control.
  - `oneof message_type`: Contains one of the following message types.
    - `CloseMsg close_msg`: Message to close the session.

### DispersalMessage
- **DispersalMessage**: Wrapper message for different types of dispersal and sampling messages.
  - `oneof message_type`: Contains one of the following message types.
    - `DispersalReq dispersal_req`: Dispersal request.
    - `DispersalRes dispersal_res`: Dispersal response.
    - `SampleReq sample_req`: Sample request.
    - `SampleRes sample_res`: Sample response.

## Protobuf

To generate the updated protobuf serializer from `dispersal.proto`, run the following command:

```bash
protoc --python_out=. dispersal.proto
```

This will generate the necessary Python code to serialize and deserialize the messages defined in the `dispersal.proto` file.
