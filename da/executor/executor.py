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
        data = "TEST DATA"
        while True:
            try:
                for transport in self.connections:
                    message = proto.new_dispersal_put_msg(data)
                    await transport.write(message)
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error during message sending: {e}")

    async def connect(self):
        try:
            reader, writer = await asyncio.open_connection(self.addr, self.port)
            conn_id = len(self.connections)
            transport = Transport(conn_id, reader, writer, self._handle)
            self.connections.append(transport)
            print(f"Connected to {self.addr}:{self.port}, ID: {conn_id}")
            asyncio.create_task(transport.read_and_process())
        except Exception as e:
            print(f"Failed to connect or lost connection: {e}")

    async def _handle(self, conn_id, writer, message):
        msg_type, msg_id, data = message
        if msg_type == proto.DISPERSAL_OK:
            print(f"Executor: Dispersal OK from connection {conn_id}, message ID {msg_id}.")
        elif msg_type == proto.SAMPLE_OK:
            print(f"Executor: Sample OK from connection {conn_id}, message ID {msg_id}.")

    async def run(self):
        await asyncio.gather(*(self.connect() for _ in range(self.col_num)))
        await self.execute()

