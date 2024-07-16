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
                message = await proto.parse_from_reader(self.reader)
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
