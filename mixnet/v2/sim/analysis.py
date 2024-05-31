from collections import Counter
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd
import seaborn
from matplotlib import pyplot as plt
import scipy.stats as stats

from adversary import NodeState
from config import Config
from simulation import Simulation

if TYPE_CHECKING:
    from node import Node


class Analysis:
    def __init__(self, sim: Simulation, config: Config):
        self.sim = sim
        self.config = config

    def run(self):
        message_size_df = self.message_size_distribution()
        self.bandwidth(message_size_df)
        self.messages_emitted_around_interval()
        self.messages_in_node_over_time()
        # self.node_states()
        self.message_hops()
        self.timing_attack()

    def bandwidth(self, message_size_df: pd.DataFrame):
        dataframes = []
        nonzero_egresses = []
        nonzero_ingresses = []
        for egress_bandwidths, ingress_bandwidths in zip(self.sim.p2p.measurement.egress_bandwidth_per_time,
                                                         self.sim.p2p.measurement.ingress_bandwidth_per_time):
            rows = []
            for node in self.sim.p2p.nodes:
                egress = egress_bandwidths[node] / 1024.0
                ingress = ingress_bandwidths[node] / 1024.0
                rows.append((node.id, egress, ingress))
                if egress > 0:
                    nonzero_egresses.append(egress)
                if ingress > 0:
                    nonzero_ingresses.append(ingress)
            df = pd.DataFrame(rows, columns=["node_id", "egress", "ingress"])
            dataframes.append(df)

        times = range(len(dataframes))
        df = pd.concat([df.assign(Time=time) for df, time in zip(dataframes, times)], ignore_index=True)
        df = df.pivot(index="Time", columns="node_id", values=["egress", "ingress"])
        plt.figure(figsize=(12, 6))
        for column in df.columns:
            marker = "x" if column[0] == "ingress" else "o"
            plt.plot(df.index, df[column], marker=marker, label=column[0])
        plt.title("Egress/ingress bandwidth of each node over time")
        plt.xlabel("Time")
        plt.ylabel("Bandwidth (KiB/s)")
        plt.ylim(bottom=0)
        # Customize the legend to show only 'egress' and 'ingress' regardless of node_id
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())
        plt.grid(True)

        # Adding descriptions on the right size of the plot
        egress_series = pd.Series(nonzero_egresses)
        ingress_series = pd.Series(nonzero_ingresses)
        desc = (
            f"message: {message_size_df["message_size"].mean():.0f} bytes\n"
            f"{self.config.description()}\n\n"
            f"[egress(>0)]\nmean: {egress_series.mean():.2f} KiB/s\nmax: {egress_series.max():.2f} KiB/s\n\n"
            f"[ingress(>0)]\nmean: {ingress_series.mean():.2f} KiB/s\nmax: {ingress_series.max():.2f} KiB/s"
        )
        plt.text(1.02, 0.5, desc, transform=plt.gca().transAxes, verticalalignment="center", fontsize=12)
        plt.subplots_adjust(right=0.8)  # Adjust layout to make room for the text

        plt.show()

    def message_size_distribution(self) -> pd.DataFrame:
        df = pd.DataFrame(self.sim.p2p.adversary.message_sizes, columns=["message_size"])
        print(df.describe())
        return df

    def messages_emitted_around_interval(self):
        df = pd.DataFrame(
            [(node.id, cnt, node.id < len(self.sim.config.mixnet.real_message_prob_weights))
             for node, cnt in self.sim.p2p.adversary.senders_around_interval.items()],
            columns=["node_id", "msg_count", "expected"]
        )
        plt.figure(figsize=(10, 6))
        seaborn.barplot(data=df, x="node_id", y="msg_count", hue="expected", palette={True: "red", False: "blue"})
        plt.title("Messages emitted around the promised interval")
        plt.xlabel("Sender Node ID")
        plt.ylabel("Msg Count")
        plt.legend(title="expected")
        plt.show()

    def messages_in_node_over_time(self):
        dataframes = []
        for i, msgs_in_node in enumerate(self.sim.p2p.adversary.msgs_in_node_per_window):
            time = i * self.config.adversary.io_window_moving_interval
            df = pd.DataFrame(
                [(time, node.id, msg_cnt, len(senders)) for node, (msg_cnt, senders) in msgs_in_node.items()],
                columns=["time", "node_id", "msg_cnt", "sender_cnt"])
            if not df.empty:
                dataframes.append(df)
        df = pd.concat(dataframes, ignore_index=True)

        msg_cnt_df = df.pivot(index="time", columns="node_id", values="msg_cnt")
        plt.figure(figsize=(12, 6))
        for column in msg_cnt_df.columns:
            plt.plot(msg_cnt_df.index, msg_cnt_df[column], marker=None, label=column)
        plt.title("Messages within each node over time")
        plt.xlabel("Time")
        plt.ylabel("Msg Count")
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        sender_cnt_df = df.pivot(index="time", columns="node_id", values="sender_cnt")
        plt.figure(figsize=(12, 6))
        for column in sender_cnt_df.columns:
            plt.plot(sender_cnt_df.index, sender_cnt_df[column], marker=None, label=column)
        plt.title("Diversity of senders of messages received by each node over time")
        plt.xlabel("Time")
        plt.ylabel("# of senders of messages received by each node")
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(12, 6))
        df.boxplot(column="sender_cnt", by="time", medianprops={"color": "red", "linewidth": 2.5})
        plt.title("Diversity of senders of messages received by each node over time")
        plt.suptitle("")
        plt.xticks([])
        plt.xlabel("Time")
        plt.ylabel("# of senders of messages received by each node")
        plt.ylim(bottom=0)
        plt.grid(axis="x")
        plt.tight_layout()
        plt.show()

    def node_states(self):
        rows = []
        for time, node_states in self.sim.p2p.adversary.node_states.items():
            for node, state in node_states.items():
                rows.append((time, node.id, state))
        df = pd.DataFrame(rows, columns=["time", "node_id", "state"])

        plt.figure(figsize=(10, 6))
        seaborn.scatterplot(data=df, x="time", y="node_id", hue="state",
                            palette={NodeState.SENDING: "red", NodeState.RECEIVING: "blue"})
        plt.title("Node states over time")
        plt.xlabel("Time")
        plt.ylabel("Node ID")
        plt.legend(title="state")
        plt.show()

    def message_hops(self):
        df = pd.DataFrame(self.sim.p2p.measurement.message_hops.values(), columns=["hops"])
        print(df.describe())
        plt.figure(figsize=(6, 6))
        seaborn.boxplot(data=df, y="hops", medianprops={"color": "red", "linewidth": 2.5})
        plt.title("Message hops distribution")
        plt.show()

    def timing_attack(self):
        """
        pick a random node received a message.
        then, track back the message to the sender
        until
        - there is no message to track back within a reasonable time window
        - enough hops have been traversed
        """
        all_results = []
        window = len(self.sim.p2p.adversary.msgs_in_node_per_window) - 1
        while window >= 0:
            items = self.sim.p2p.adversary.msgs_in_node_per_window[window].items()
            actual_receivers = [node for node, (msg_cnt, senders) in items if len(senders) > 0]
            if len(actual_receivers) == 0:
                window -= 1
                continue

            results = []
            max_hops = 0
            for receiver in actual_receivers:
                nodes_per_hop = self.timing_attack_with(receiver, window)
                self.print_nodes_per_hop(nodes_per_hop, window)
                results.append(nodes_per_hop)
                max_hops = max(max_hops, len(nodes_per_hop))
            window -= max_hops
            all_results.extend(results)

        suspected_senders = Counter()
        for result in all_results:
            print(Counter({node.id: count for node, count in result[-1].items()}))
            suspected_senders.update(result[-1])
        suspected_senders = ({node.id: count for node, count in suspected_senders.items()})
        print(f"suspected nodes count: {len(suspected_senders)}")

        # Extract keys and values from the Counter
        keys = list(suspected_senders.keys())
        values = list(suspected_senders.values())
        # Create the bar plot
        plt.figure(figsize=(12, 8))
        plt.bar(keys, values)
        plt.xlabel('Node ID')
        plt.ylabel('Counts')
        plt.title('Suspected Sender Counts')
        plt.show()

        # Create the bar plot for original sender counts
        original_senders = ({node.id: count for node, count in self.sim.p2p.measurement.original_senders.items()})
        plt.figure(figsize=(12, 8))
        plt.bar(list(original_senders.keys()), list(original_senders.values()))
        plt.xlabel('Node ID')
        plt.ylabel('Counts')
        plt.title('Original Sender Counts')
        plt.show()

        # Create the bar plot for original sender counts
        broadcasters = ({node.id: count for node, count in self.sim.p2p.broadcasters.items()})
        plt.figure(figsize=(12, 8))
        plt.bar(list(broadcasters.keys()), list(broadcasters.values()))
        plt.xlabel('Node ID')
        plt.ylabel('Counts')
        plt.title('Broadcasters')
        plt.show()

        # Calculate the mean and standard deviation of the counts
        mean = np.mean(values)
        std_dev = np.std(values)
        # Plot the histogram of the values
        plt.figure(figsize=(12, 8))
        plt.hist(values, bins=30, density=True, alpha=0.6, color='g', label='Counts Histogram')
        # Plot the normal distribution curve
        xmin, xmax = plt.xlim()
        x = np.linspace(xmin, xmax, 100)
        p = stats.norm.pdf(x, mean, std_dev)
        plt.plot(x, p, 'k', linewidth=2, label='Normal Distribution')
        title = "Fit results: mean = %.2f,  std_dev = %.2f" % (mean, std_dev)
        plt.title(title)
        plt.xlabel('Counts')
        plt.ylabel('Density')
        plt.legend()
        plt.show()

    def timing_attack_with(self, starting_node: "Node", starting_window: int):
        _, senders = self.sim.p2p.adversary.msgs_in_node_per_window[starting_window][starting_node]
        nodes_per_hop = [Counter(senders)]

        if self.config.p2p.type == self.config.p2p.TYPE_ONE_TO_ALL:
            MAX_HOPS = 1 + self.config.mixnet.num_mix_layers
        else:
            MAX_HOPS = (1 + self.config.mixnet.num_mix_layers) * 4

        for window in range(starting_window - 1, 0, -1):
            if len(nodes_per_hop) >= MAX_HOPS:
                break

            next_nodes = Counter()
            for node in nodes_per_hop[-1]:
                _, senders = self.sim.p2p.adversary.msgs_in_node_per_window[window][node]
                next_nodes.update(senders)
            if len(next_nodes) == 0:
                break
            nodes_per_hop.append(next_nodes)

        return nodes_per_hop

    @staticmethod
    def print_nodes_per_hop(nodes_per_hop, starting_window: int):
        for hop, nodes in enumerate(nodes_per_hop):
            print(f"hop-{hop} from w-{starting_window}: {len(nodes)} nodes: {sorted([node.id for node in nodes])}")
