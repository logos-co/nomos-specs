import asyncio
import argparse
import proto
from itertools import count

conn_id_counter = count(start=1)

class MockTransport:
    def __init__(self, conn_id, reader, writer, handler):
        self.conn_id = conn_id
        self.reader = reader
        self.writer = writer
        self.handler = handler

    async def read_and_process(self):
        try:
            while True:
                message = await proto.unpack_from_reader(self.reader)
                await self.handler(self.conn_id, self.writer, message)
        except Exception as e:
            print(f"MockTransport: An error occurred: {e}")
        finally:
            self.writer.close()
            await self.writer.wait_closed()

    async def write(self, message):
        self.writer.write(message)
        await self.writer.drain()


class MockNode:
    def __init__(self, addr, port, handler=None):
        self.addr = addr
        self.port = port
        self.handler = handler if handler else self._handle

    async def _on_conn(self, reader, writer):
        conn_id = next(conn_id_counter)
        transport = MockTransport(conn_id, reader, writer, self.handler)
        await transport.read_and_process()

    async def _handle(self, conn_id, writer, message):
        if message.HasField('dispersal_req'):
            blob_id = message.dispersal_req.blob.blob_id
            data = message.dispersal_req.blob.data
            print(f"MockNode: Received DispersalRes: blob_id={blob_id}; data={data}")
            # Imitate succesful verification.
            writer.write(proto.new_dispersal_res_success_msg(blob_id))
        elif message.HasField('sample_req'):
            print(f"MockNode: Received SampleRes: blob_id={message.sample_req.blob_id}")
        else:
            print(f"MockNode: Received unknown message: {message} ")

    async def run(self):
        server = await asyncio.start_server(
            self._on_conn, self.addr, self.port
        )
        print(f"MockNode: Server started at {self.addr}:{self.port}")
        async with server:
            await server.serve_forever()


class MockExecutor:
    def __init__(self, addr, port, col_num, executor=None, handler=None):
        self.addr = addr
        self.port = port
        self.col_num = col_num
        self.connections = []
        self.interval = 10
        self.executor = executor if executor else self._execute
        self.handler = handler if handler else self._handle

    async def _execute(self):
        message = proto.new_dispersal_req_msg(b"dummy_blob_id", b"dummy_data")
        while True:
            try:
                await asyncio.gather(*[t.write(message) for t in self.connections])
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"MockExecutor: Error during message sending: {e}")

    async def _handle(self, conn_id, writer, message):
        if message.HasField('dispersal_res'):
            print(f"MockExecutor: Received DispersalRes: blob_id={message.dispersal_res.blob_id}")
        elif message.HasField('sample_res'):
            print(f"MockExecutor: Received SampleRes: blob_id={message.sample_res.blob_id}")
        else:
            print(f"MockExecutor: Received unknown message: {message}")

    async def _connect(self):
        try:
            reader, writer = await asyncio.open_connection(self.addr, self.port)
            conn_id = len(self.connections)
            transport = MockTransport(conn_id, reader, writer, self.handler)
            self.connections.append(transport)
            print(f"MockExecutor: Connected to {self.addr}:{self.port}, ID: {conn_id}")
            asyncio.create_task(transport.read_and_process())
        except Exception as e:
            print(f"MockExecutor: Failed to connect or lost connection: {e}")

    async def run(self):
        await asyncio.gather(*(self._connect() for _ in range(self.col_num)))
        await self.executor()


class MockSystem:
    def __init__(self, addr='localhost'):
        self.addr = addr

    async def run_node_with_executor(self, col_number):
        node = MockNode(self.addr, 8888)
        executor = MockExecutor(self.addr, 8888, col_number)
        await asyncio.gather(node.run(), executor.run())


def main():
    app = MockSystem()
    asyncio.run(app.run_node_with_executor(1))

if __name__ == '__main__':
    main()
