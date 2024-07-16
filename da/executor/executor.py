import asyncio
import proto
from transport import Transport

class Executor:
    def __init__(self, addr, port, col_num):
        self.addr = addr
        self.port = port
        self.col_num = col_num
        self.connections = []
        self.interval = 10

    async def execute(self):
        message = proto.new_dispersal_req_msg(b"dummy_blob_id", b"dummy_data")
        while True:
            try:
                # TODO: Mock original data conversion into blobs.
                await asyncio.gather(*[t.write(message) for t in self.connections])
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Executor: Error during message sending: {e}")

    async def connect(self):
        try:
            reader, writer = await asyncio.open_connection(self.addr, self.port)
            conn_id = len(self.connections)
            transport = Transport(conn_id, reader, writer, self._handle)
            self.connections.append(transport)
            print(f"Executor: Connected to {self.addr}:{self.port}, ID: {conn_id}")
            asyncio.create_task(transport.read_and_process())
        except Exception as e:
            print(f"Executor: Failed to connect or lost connection: {e}")

    async def _handle(self, conn_id, writer, message):
        if message.HasField('dispersal_res'):
            print(f"Executor: Received DispersalRes: blob_id={message.dispersal_res.blob_id}")
        elif message.HasField('sample_res'):
            print(f"Executor: Received SampleRes: blob_id={message.sample_res.blob_id}")
        else:
            print(f"Executor: Received unknown message: {message}")

    async def run(self):
        await asyncio.gather(*(self.connect() for _ in range(self.col_num)))
        await self.execute()
