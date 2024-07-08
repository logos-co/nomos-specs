import asyncio
import struct
import proto

class Transport:
    def __init__(self, conn_id, reader, writer, handler):
        self.conn_id = conn_id
        self.reader = reader
        self.writer = writer
        self.handler = handler

    async def read_and_process(self):
        try:
            while True:
                header = await self.reader.readexactly(9)  # Assuming the header is 9 bytes long
                msg_type, msg_id, data_length = proto.unpack_header(header)
                data = await self.reader.readexactly(data_length)
                await self.handler(self.conn_id, self.writer, (msg_type, msg_id, data))
        except asyncio.IncompleteReadError:
            print("Transport: Connection closed by the peer.")
        except Exception as e:
            print(f"Transport: An error occurred: {e}")
        finally:
            self.writer.close()
            await self.writer.wait_closed()

    async def write(self, data):
        self.writer.write(data)
        await self.writer.drain()

