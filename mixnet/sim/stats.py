from collections import Counter

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

    def analyze(self):
        self._message_sizes()
        self._bandwidths_per_conn()
        self._bandwidths_per_node()

    def _message_sizes(self):
        sizes = Counter()
        for _, (_, outbound_conns) in self.conns_per_node.items():
            for conn in outbound_conns:
                sizes.update(conn.msg_sizes)

        df = pandas.DataFrame.from_dict(sizes, orient="index").reset_index()
        df.columns = ["msg_size", "count"]
        print(df)

    def _bandwidths_per_conn(self):
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
        plt.show()

    def _bandwidths_per_node(self):
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
        plt.show()
