from collections import Counter, defaultdict

import matplotlib.pyplot as plt
import pandas

from mixnet.node import Node
from mixnet.sim.connection import MeteredRemoteSimplexConnection

# A map of nodes to their inbound/outbound connections
NodeConnectionsMap = dict[
    Node,
    tuple[list[MeteredRemoteSimplexConnection], list[MeteredRemoteSimplexConnection]],
]


class ConnectionStats:
    def __init__(self):
        self.conns_per_node: NodeConnectionsMap = defaultdict(lambda: ([], []))

    def register(
        self,
        node: Node,
        inbound_conn: MeteredRemoteSimplexConnection,
        outbound_conn: MeteredRemoteSimplexConnection,
    ):
        self.conns_per_node[node][0].append(inbound_conn)
        self.conns_per_node[node][1].append(outbound_conn)

    def analyze(self):
        self.__message_sizes()
        self.__bandwidths_per_conn()
        self.__bandwidths_per_node()

    def __message_sizes(self):
        """
        Analyzes all message sizes sent across all connections of all nodes.
        """
        sizes: Counter[int] = Counter()
        for _, (_, outbound_conns) in self.conns_per_node.items():
            for conn in outbound_conns:
                sizes.update(conn.msg_sizes)

        df = pandas.DataFrame.from_dict(sizes, orient="index").reset_index()
        df.columns = ["msg_size", "count"]
        print("==========================================")
        print(" Message Size Distribution")
        print("==========================================")
        print(f"{df}\n")

    def __bandwidths_per_conn(self):
        """
        Analyzes the bandwidth consumed by each simplex connection.
        """
        plt.plot(figsize=(12, 6))

        for _, (_, outbound_conns) in self.conns_per_node.items():
            for conn in outbound_conns:
                sending_bandwidths = conn.sending_bandwidths().map(lambda x: x / 1024)
                plt.plot(sending_bandwidths.index, sending_bandwidths)

        plt.title("Unidirectional Bandwidths per Connection")
        plt.xlabel("Time (s)")
        plt.ylabel("Bandwidth (KiB/s)")
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.tight_layout()
        plt.draw()

    def __bandwidths_per_node(self):
        """
        Analyzes the inbound/outbound bandwidths consumed by each node (sum of all its connections).
        """
        _, axs = plt.subplots(nrows=2, ncols=1, figsize=(12, 6))

        for i, (_, (inbound_conns, outbound_conns)) in enumerate(
            self.conns_per_node.items()
        ):
            inbound_bandwidths = (
                pandas.concat(
                    [conn.receiving_bandwidths() for conn in inbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024)
            )
            outbound_bandwidths = (
                pandas.concat(
                    [conn.sending_bandwidths() for conn in outbound_conns], axis=1
                )
                .sum(axis=1)
                .map(lambda x: x / 1024)
            )
            axs[0].plot(inbound_bandwidths.index, inbound_bandwidths, label=f"Node-{i}")
            axs[1].plot(
                outbound_bandwidths.index, outbound_bandwidths, label=f"Node-{i}"
            )

        axs[0].set_title("Inbound Bandwidths per Node")
        axs[0].set_xlabel("Time (s)")
        axs[0].set_ylabel("Bandwidth (KiB/s)")
        axs[0].legend()
        axs[0].set_ylim(bottom=0)
        axs[0].grid(True)

        axs[1].set_title("Outbound Bandwidths per Node")
        axs[1].set_xlabel("Time (s)")
        axs[1].set_ylabel("Bandwidth (KiB/s)")
        axs[1].legend()
        axs[1].set_ylim(bottom=0)
        axs[1].grid(True)

        plt.tight_layout()
        plt.draw()
