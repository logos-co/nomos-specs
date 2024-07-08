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
        print(f"Server started at {self.addr}:{self.port}")
        async with server:
            await server.serve_forever()

    async def _handle(self, conn_id, writer, message):
        msg_type, msg_id, data = message
        if msg_type == proto.DISPERSAL_PUT:
            response = proto.new_dispersal_ok_msg(msg_id)
            writer.write(response)
        elif msg_type == proto.SAMPLE_PUT:
            pass

    async def run(self):
        await self.listen()
