import trio
from node import DANode


class DANetwork:
    num_nodes: int
    nodes: []

    def __init__(self, nodes):
        self.num_nodes = nodes
        self.nodes = []

    async def build(self, nursery, shutdown):
        port_idx = 7560
        for _ in range(self.num_nodes):
            port_idx += 1
            nursery.start_soon(DANode.new, port_idx, self.nodes, nursery, shutdown)
        print("net built")

    def get_nodes(self):
        return self.nodes
