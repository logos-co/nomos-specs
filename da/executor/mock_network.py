import asyncio
import argparse
from node import Node
from executor import Executor

class App:
    def __init__(self, addr='localhost'):
        self.addr = addr

    async def run_nodes(self, start_port, num_nodes):
        nodes = [Node(self.addr, start_port + i) for i in range(num_nodes)]
        await asyncio.gather(*(node.run() for node in nodes))

    async def run_node_with_executor(self, col_number):
        node = Node(self.addr, 8888)
        executor = Executor(self.addr, 8888, col_number)
        await asyncio.gather(node.run(), executor.run())

    async def run_executor(self, remote_addr, start_port, col_number):
        executor = Executor(remote_addr, start_port, col_number)
        await asyncio.gather(executor.run())

def main():
    # TODO: Add args parser.
    app = App()

    asyncio.run(app.run_node_with_executor(1))

if __name__ == '__main__':
    main()

