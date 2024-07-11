import asyncio
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
                length_prefix = await self.reader.readexactly(proto.MAX_MSG_LEN_BYTES)
                data_length = int.from_bytes(length_prefix, byteorder='big')
                
                data = await self.reader.readexactly(data_length)
                message = proto.unpack_message(data)
                
                await self.handler(self.conn_id, self.writer, message)
        except asyncio.IncompleteReadError:
            print("Transport: Connection closed by the peer.")
        except Exception as e:
            print(f"Transport: An error occurred: {e}")
        finally:
            self.writer.close()
            await self.writer.wait_closed()

    async def write(self, message):
        self.writer.write(message)
        await self.writer.drain()


