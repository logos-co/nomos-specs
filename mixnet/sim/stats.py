import matplotlib.pyplot as plt
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
        plt.figure(figsize=(12, 6))

        plt.subplot(2, 1, 1)

        for i, (_, (inbound_conns, _)) in enumerate(self.conns_per_node.items()):
            inbound_bandwidths = (
                pandas.concat(
                    [conn.input_bandwidths() for conn in inbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024)
            )
            plt.plot(inbound_bandwidths.index, inbound_bandwidths, label=f"Node-{i}")

        plt.xlabel("Time (s)")
        plt.ylabel("Bandwidth (KB/s)")
        plt.title("Inbound Bandwidths per Node")
        plt.legend()
        plt.ylim(bottom=0)
        plt.grid(True)

        plt.subplot(2, 1, 2)

        for i, (_, (_, outbound_conns)) in enumerate(self.conns_per_node.items()):
            outbound_bandwidths = (
                pandas.concat(
                    [conn.output_bandwidths() for conn in outbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024)
            )
            plt.plot(outbound_bandwidths.index, outbound_bandwidths, label=f"Node-{i}")

        plt.xlabel("Time (s)")
        plt.ylabel("Bandwidth (KB/s)")
        plt.title("Outbound Bandwidths per Node")
        plt.legend()
        plt.ylim(bottom=0)
        plt.grid(True)

        plt.tight_layout()
