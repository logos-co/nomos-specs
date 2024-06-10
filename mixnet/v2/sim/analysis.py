from collections import Counter
from typing import TYPE_CHECKING

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from adversary import NodeState
from config import Config
from simulation import Simulation

if TYPE_CHECKING:
    from node import Node

COL_TIME = "Time"
COL_NODE_ID = "Node ID"
COL_MSG_CNT = "Message Count"
COL_SENDER_CNT = "Sender Count"
COL_NODE_STATE = "Node State"
COL_HOPS = "Hops"
COL_EXPECTED = "Expected"
COL_MSG_SIZE = "Message Size"
COL_EGRESS = "Egress"
COL_INGRESS = "Ingress"
COL_SUCCESS_RATE = "Success Rate (%)"


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
        median_hops = self.message_hops()
        self.timing_attack(median_hops)

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
            df = pd.DataFrame(rows, columns=[COL_NODE_ID, COL_EGRESS, COL_INGRESS])
            dataframes.append(df)

        times = range(len(dataframes))
        df = pd.concat([df.assign(Time=time) for df, time in zip(dataframes, times)], ignore_index=True)
        df = df.pivot(index=COL_TIME, columns=COL_NODE_ID, values=[COL_EGRESS, COL_INGRESS])
        plt.figure(figsize=(12, 6))
        for column in df.columns:
            marker = "x" if column[0] == COL_INGRESS else "o"
            plt.plot(df.index, df[column], marker=marker, label=column[0])
        plt.title("Egress/ingress bandwidth of each node over time")
        plt.xlabel(COL_TIME)
        plt.ylabel("Bandwidth (KiB/s)")
        plt.ylim(bottom=0)
        # Customize the legend to show only "egress" and "ingress" regardless of node_id
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())
        plt.grid(True)

        # Adding descriptions on the right size of the plot
        egress_series = pd.Series(nonzero_egresses)
        ingress_series = pd.Series(nonzero_ingresses)
        desc = (
            f"message: {message_size_df[COL_MSG_SIZE].mean():.0f} bytes\n"
            f"{self.config.description()}\n\n"
            f"[egress(>0)]\nmean: {egress_series.mean():.2f} KiB/s\nmax: {egress_series.max():.2f} KiB/s\n\n"
            f"[ingress(>0)]\nmean: {ingress_series.mean():.2f} KiB/s\nmax: {ingress_series.max():.2f} KiB/s"
        )
        plt.text(1.02, 0.5, desc, transform=plt.gca().transAxes, verticalalignment="center", fontsize=12)
        plt.subplots_adjust(right=0.8)  # Adjust layout to make room for the text

        plt.show()

    def message_size_distribution(self) -> pd.DataFrame:
        df = pd.DataFrame(self.sim.p2p.adversary.message_sizes, columns=[COL_MSG_SIZE])
        print(df.describe())
        return df

    def messages_emitted_around_interval(self):
        # A ground truth that shows how many times each node sent a real message
        truth_df = pd.DataFrame(
            [(node.id, count) for node, count in self.sim.p2p.measurement.original_senders.items()],
            columns=[COL_NODE_ID, COL_MSG_CNT])
        # A result of observing nodes who have sent messages around the promised message interval
        suspected_df = pd.DataFrame(
            [(node.id, self.sim.p2p.adversary.senders_around_interval[node]) for node in
             self.sim.p2p.measurement.original_senders.keys()],
            columns=[COL_NODE_ID, COL_MSG_CNT]
        )

        width = 0.4
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.bar(truth_df[COL_NODE_ID] - width / 2, truth_df[COL_MSG_CNT], width, label="Ground Truth", color="b")
        ax.bar(truth_df[COL_NODE_ID] + width / 2, suspected_df[COL_MSG_CNT], width, label="Adversary's Inference",
               color="r")
        ax.set_title("Nodes who generated real messages")
        ax.set_xlabel(COL_NODE_ID)
        ax.set_ylabel(COL_MSG_CNT)
        ax.set_xlim(-1, len(truth_df[COL_NODE_ID]))
        ax.legend()
        plt.tight_layout()
        plt.show()

        # Calculate precision, recall, and F1 score
        truth = set(truth_df[truth_df[COL_MSG_CNT] > 0][COL_NODE_ID])
        suspected = set(suspected_df[suspected_df[COL_MSG_CNT] > 0][COL_NODE_ID])
        true_positives = truth.intersection(suspected)
        precision = len(true_positives) / len(suspected) * 100.0 if len(suspected) > 0 else 0.0
        recall = len(true_positives) / len(truth) * 100.0 if len(truth) > 0 else 0.0
        f1_score = 2 * precision * recall / (precision + recall) if precision + recall > 0 else 0.0
        print(f"Precision: {precision:.2f}%, Recall: {recall:.2f}%, F1 Score: {f1_score:.2f}%")

    def messages_in_node_over_time(self):
        dataframes = []
        for window, msg_pools in enumerate(self.sim.p2p.adversary.msg_pools_per_window):
            time = window * self.config.adversary.window_size
            data = []
            for receiver, msg_pool in msg_pools.items():
                senders = self.sim.p2p.adversary.msgs_received_per_window[window][receiver]
                data.append((time, receiver.id, len(msg_pool), len(senders)))
            df = pd.DataFrame(data, columns=[COL_TIME, COL_NODE_ID, COL_MSG_CNT, COL_SENDER_CNT])
            if not df.empty:
                dataframes.append(df)
        df = pd.concat(dataframes, ignore_index=True)

        msg_cnt_df = df.pivot(index=COL_TIME, columns=COL_NODE_ID, values=COL_MSG_CNT)
        plt.figure(figsize=(12, 6))
        for column in msg_cnt_df.columns:
            plt.plot(msg_cnt_df.index, msg_cnt_df[column], marker=None, label=column)
        plt.title("Messages within each node over time")
        plt.xlabel(COL_TIME)
        plt.ylabel(COL_MSG_CNT)
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        sender_cnt_df = df.pivot(index=COL_TIME, columns=COL_NODE_ID, values=COL_SENDER_CNT)
        plt.figure(figsize=(12, 6))
        for column in sender_cnt_df.columns:
            plt.plot(sender_cnt_df.index, sender_cnt_df[column], marker=None, label=column)
        plt.title("Diversity of senders of messages received by each node over time")
        plt.xlabel(COL_TIME)
        plt.ylabel("# of senders of messages received by each node")
        plt.ylim(bottom=0)
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        plt.figure(figsize=(12, 6))
        df.boxplot(column=COL_SENDER_CNT, by=COL_TIME, medianprops={"color": "red", "linewidth": 2.5})
        plt.title("Diversity of senders of messages received by each node over time")
        plt.suptitle("")
        plt.xticks([])
        plt.xlabel(COL_TIME)
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
        df = pd.DataFrame(rows, columns=[COL_TIME, COL_NODE_ID, COL_NODE_STATE])

        plt.figure(figsize=(10, 6))
        seaborn.scatterplot(data=df, x=COL_TIME, y=COL_NODE_ID, hue=COL_NODE_STATE,
                            palette={NodeState.SENDING: "red", NodeState.RECEIVING: "blue"})
        plt.title("Node states over time")
        plt.xlabel(COL_TIME)
        plt.ylabel(COL_NODE_ID)
        plt.legend(title=COL_NODE_STATE)
        plt.show()

    def message_hops(self) -> int:
        df = pd.DataFrame(self.sim.p2p.measurement.message_hops.values(), columns=[COL_HOPS])
        print(df.describe())
        plt.figure(figsize=(6, 6))
        seaborn.boxplot(data=df, y=COL_HOPS, medianprops={"color": "red", "linewidth": 2.5})
        plt.ylim(bottom=0)
        plt.title("Message hops distribution")
        plt.show()
        return int(df.median().iloc[0])

    def timing_attack(self, hops_between_layers: int):
        hops_to_observe = hops_between_layers * (self.config.mixnet.num_mix_layers + 1)
        success_rates = []
        for receiver, windows_and_msgs in self.sim.p2p.adversary.final_msgs_received.items():
            for window, senders_and_origins in windows_and_msgs.items():
                for sender, origin_id in senders_and_origins:
                    print(f"START: receiver:{receiver.id}, window:{window}, sender:{sender.id}, origin:{origin_id}")
                    suspected_origins = Counter()
                    self.timing_attack_with(receiver, window, hops_to_observe, 0, suspected_origins, sender)
                    suspected_origin_ids = {node.id for node in suspected_origins}
                    if origin_id in suspected_origin_ids:
                        success_rate = 1 / len(suspected_origin_ids) * 100.0
                    else:
                        success_rate = 0.0
                    print(
                        f"END: origin:{origin_id}, suspected_origins:{suspected_origin_ids}, success_rate:{success_rate:.2f}%"
                    )
                    success_rates.append(success_rate)

        df = pd.DataFrame(success_rates, columns=[COL_SUCCESS_RATE])
        print(df.describe())
        plt.figure(figsize=(6, 6))
        plt.boxplot(df[COL_SUCCESS_RATE], vert=True, patch_artist=True, boxprops=dict(facecolor="lightblue"),
                    medianprops=dict(color="orange"))
        mean = df[COL_SUCCESS_RATE].mean()
        median = df[COL_SUCCESS_RATE].median()
        plt.axhline(mean, color="red", linestyle="--", linewidth=1, label=f"Mean: {mean:.2f}%")
        plt.axhline(median, color="orange", linestyle="-", linewidth=1, label=f"Median: {median:.2f}%")
        plt.ylabel(COL_SUCCESS_RATE)
        plt.ylim(-5, 105)
        plt.title("Timing attack success rate distribution")
        plt.legend()
        plt.grid(True)
        plt.show()

    def timing_attack_with(self, receiver: "Node", window: int, remaining_hops: int, observed_hops: int,
                           suspected_origins: Counter,
                           sender: "Node" = None):
        assert remaining_hops >= 1
        # If all nodes are already suspected, no need to inspect further.
        if len(suspected_origins) == len(self.sim.p2p.nodes):
            return

        # Start inspecting senders who sent messages that were arrived in the receiver at the given window.
        # If the specific sender is given, inspect only that sender to maximize the success rate.
        if sender is not None:
            senders = {sender}
        else:
            senders = self.sim.p2p.adversary.msgs_received_per_window[window][receiver]

        # Suspect the receiver as the origin, if the receiver has not received any messages at the given window,
        # and if the minimum number of hops has been observed.
        if len(senders) == 0 and observed_hops > self.sim.config.mixnet.num_mix_layers:
            suspected_origins.update({receiver})
            return

        # If the remaining_hops is 1, return the senders as suspected senders
        if remaining_hops == 1:
            suspected_origins.update(senders)
            return

        # Inspect each sender who sent messages to the receiver
        for sender in senders:
            # Track back to each window where that sender might have received any messages.
            time_range = self.config.mixnet.max_mix_delay + self.config.p2p.max_network_latency
            window_range = int(time_range / self.config.adversary.window_size)
            for prev_window in range(window - 1, window - 1 - window_range, -1):
                if prev_window < 0:
                    break
                self.timing_attack_with(sender, prev_window, remaining_hops - 1, observed_hops + 1, suspected_origins)

    @staticmethod
    def print_nodes_per_hop(nodes_per_hop, starting_window: int):
        for hop, nodes in enumerate(nodes_per_hop):
            print(f"hop-{hop} from w-{starting_window}: {len(nodes)} nodes: {sorted([node.id for node in nodes])}")
