import trio
from constants import DEBUG, NODE_PORT_BASE
from node import DANode


class DANetwork:
    """
    Lightweight wrapper around a network of DA nodes.
    Really just creates the network for now
    """

    num_nodes: int
    nodes: []

    def __init__(self, nodes):
        self.num_nodes = nodes
        self.nodes = []

    async def build(self, nursery, shutdown, disperse_send):
        port_idx = NODE_PORT_BASE
        for _ in range(self.num_nodes):
            port_idx += 1
            nursery.start_soon(
                DANode.new,
                port_idx,
                self.nodes,
                nursery,
                shutdown,
                disperse_send.clone(),
            )
        if DEBUG:
            print("net built")

    def get_nodes(self):
        return self.nodes
