import pandas

from mixnet.node import Node
from mixnet.sim.connection import MeteredRemoteSimplexConnection

NodeConnectionsMap = dict[
    Node,
    tuple[list[MeteredRemoteSimplexConnection], list[MeteredRemoteSimplexConnection]],
]


class ConnectionStats:
    conns_per_node: NodeConnectionsMap

    def __init__(self):
        self.conns_per_node = dict()

    def register(
        self,
        node: Node,
        inbound_conn: MeteredRemoteSimplexConnection,
        outbound_conn: MeteredRemoteSimplexConnection,
    ):
        if node not in self.conns_per_node:
            self.conns_per_node[node] = ([], [])
        self.conns_per_node[node][0].append(inbound_conn)
        self.conns_per_node[node][1].append(outbound_conn)

    def bandwidths(self):
        for i, (_, (inbound_conns, outbound_conns)) in enumerate(
            self.conns_per_node.items()
        ):
            inbound_bandwidths = (
                pandas.concat(
                    [conn.input_bandwidths() for conn in inbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024 / 1024)
            )
            outbound_bandwidths = (
                pandas.concat(
                    [conn.output_bandwidths() for conn in outbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024 / 1024)
            )

            print(f"=== [Node:{i}] ===")
            print("--- Inbound bandwidths ---")
            print(inbound_bandwidths.describe())
            print("--- Outbound bandwidths ---")
            print(outbound_bandwidths.describe())
