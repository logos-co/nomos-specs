import asyncio
import struct
import proto
from itertools import count
from transport import Transport

conn_id_counter = count(start=1)

class Node:
    def __init__(self, addr, port):
        self.addr = addr
        self.port = port

    async def _on_conn(self, reader, writer):
        conn_id = next(conn_id_counter)
        transport = Transport(conn_id, reader, writer, self._handle)
        await transport.read_and_process()

    async def listen(self):
        server = await asyncio.start_server(
            self._on_conn, self.addr, self.port
        )
        print(f"Node: Server started at {self.addr}:{self.port}")
        async with server:
            await server.serve_forever()

    async def _handle(self, conn_id, writer, message):
        if message.HasField('dispersal_req'):
            blob_id = message.dispersal_req.blob.blob_id
            data = message.dispersal_req.blob.data
            print(f"Node: Received DispersalRes: blob_id={blob_id}; data={data}")
            # Imitate succesful verification.
            writer.write(proto.new_dispersal_res_success_msg(blob_id))
        elif message.HasField('sample_req'):
            print(f"Node: Received SampleRes: blob_id={message.sample_req.blob_id}")
        else:
            print(f"Node: Received unknown message: {message} ")

    async def run(self):
        await self.listen()
