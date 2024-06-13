import itertools
import multiprocessing
import sys
import threading
from collections import Counter
from typing import TYPE_CHECKING

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from adversary import NodeState
from config import Config
from environment import Time
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
    def __init__(self, sim: Simulation, config: Config, show_plots: bool = True):
        self.sim = sim
        self.config = config
        self.show_plots = show_plots

    def run(self):
        message_size_df = self.message_size_distribution()
        self.bandwidth(message_size_df)
        self.messages_emitted_around_interval()
        self.messages_in_node_over_time()
        # self.node_states()
        median_hops = self.message_hops()
        self.timing_attack(median_hops)

    def bandwidth(self, message_size_df: pd.DataFrame):
        if not self.show_plots:
            return

        dataframes = []
        nonzero_egresses = []
        nonzero_ingresses = []
        for egress_bandwidths, ingress_bandwidths in zip(self.sim.p2p.measurement.egress_bandwidth_per_sec,
                                                         self.sim.p2p.measurement.ingress_bandwidth_per_sec):
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

    def messages_emitted_around_interval(self) -> (float, float, float):
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

        if self.show_plots:
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
        return precision, recall, f1_score

    def messages_in_node_over_time(self):
        if not self.show_plots:
            return

        dataframes = []
        for time, msg_pools in enumerate(self.sim.p2p.adversary.msg_pools_per_time):
            data = []
            for receiver, msg_pool in msg_pools.items():
                senders = self.sim.p2p.adversary.msgs_received_per_time[time][receiver].keys()
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
        if not self.show_plots:
            return

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
        if self.show_plots:
            plt.figure(figsize=(6, 6))
            seaborn.boxplot(data=df, y=COL_HOPS, medianprops={"color": "red", "linewidth": 2.5})
            plt.ylim(bottom=0)
            plt.title("The distribution of max hops of single broadcasting")
            plt.show()
        return int(df.median().iloc[0])

    def timing_attack(self, hops_between_layers: int) -> pd.DataFrame:
        success_rates = self.spawn_timing_attacks(hops_between_layers)
        df = pd.DataFrame(success_rates, columns=[COL_SUCCESS_RATE])
        print(df.describe())

        if self.show_plots:
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

        return df

    def spawn_timing_attacks(self, hops_between_layers: int) -> list[float]:
        tasks = self.prepare_timing_attack_tasks(hops_between_layers)
        print(f"{len(tasks)} TASKS")

        # Spawn process for each task
        processes = []
        accuracy_results = multiprocessing.Manager().list()
        for task in tasks:
            process = multiprocessing.Process(target=self.spawn_timing_attack, args=(task, accuracy_results))
            process.start()
            processes.append(process)

        # Join processes using threading to apply a timeout to all processes almost simultaneously.
        threads = []
        for process in processes:
            thread = threading.Thread(target=Analysis.join_process,
                                      args=(process, self.config.adversary.timing_attack_timeout))
            thread.start()
            threads.append(thread)
        for thread in threads:
            thread.join()

        return list(accuracy_results)

    def spawn_timing_attack(self, task, accuracy_results):
        origin_id, receiver, time_received, remaining_hops, observed_hops, senders = task
        result = self.run_and_evaluate_timing_attack(
            origin_id, receiver, time_received, remaining_hops, observed_hops, senders
        )
        accuracy_results.append(result)
        print(f"{len(accuracy_results)} PROCESSES DONE")

    @staticmethod
    def join_process(process, timeout):
        process.join(timeout)
        if process.is_alive():
            process.terminate()
            process.join()
            print(f"PROCESS TIMED OUT")

    def prepare_timing_attack_tasks(self, hops_between_layers: int) -> list:
        hops_to_observe = hops_between_layers * (self.config.mixnet.num_mix_layers + 1)
        tasks = []

        # Prepare a task for each real message received by the adversary
        for receiver, times_and_msgs in self.sim.p2p.adversary.final_msgs_received.items():
            for time_received, msgs in times_and_msgs.items():
                for sender, time_sent, origin_id in msgs:
                    tasks.append((
                        origin_id, receiver, time_received, hops_to_observe, 0, {sender: [time_sent]}
                    ))
                    if len(tasks) >= self.config.adversary.timing_attack_max_targets:
                        return tasks

        return tasks

    def run_and_evaluate_timing_attack(self, origin_id: int, receiver: "Node", time_received: Time,
                                       remaining_hops: int, observed_hops: int,
                                       senders: dict["Node", list[Time]] = None) -> float:
        suspected_origins = self.timing_attack_from_receiver(
            receiver, time_received, remaining_hops, observed_hops, Counter(), senders
        )
        if origin_id in suspected_origins:
            return 1 / len(suspected_origins) * 100.0
        else:
            return 0.0

    def timing_attack_from_receiver(self, receiver: "Node", time_received: Time,
                                    remaining_hops: int, observed_hops: int, suspected_origins: Counter,
                                    senders: dict["Node", list[Time]] = None) -> Counter:
        if remaining_hops <= 0:
            return suspected_origins

        # If all nodes are already suspected, no need to inspect further.
        if len(suspected_origins) == self.config.mixnet.num_nodes:
            return suspected_origins

        # Start inspecting senders who sent messages that were arrived in the receiver at the given time.
        # If the specific sender is given, inspect only that sender to maximize the success rate.
        if senders is None:
            senders = self.sim.p2p.adversary.msgs_received_per_time[time_received][receiver]

        senders = dict(itertools.islice(senders.items(), self.config.adversary.timing_attack_max_pool_size))

        # Inspect each sender who sent messages to the receiver
        for sender, times_sent in senders.items():
            # Calculate the time range where the sender might have received any messages
            # related to the message being traced.
            min_time, max_time = sys.maxsize, 0
            for time_sent in times_sent:
                min_time = min(min_time, time_sent - self.config.mixnet.max_mix_delay)
                max_time = max(max_time, time_sent - self.config.mixnet.min_mix_delay)
                # If the sender is sent the message around the message interval, suspect the sender as the origin.
                if (self.sim.p2p.adversary.is_around_message_interval(time_sent)
                        and observed_hops + 1 >= self.min_hops_to_observe_for_timing_attack()):
                    suspected_origins.update({sender.id})

            # Track back to each time when that sender might have received any messages.
            for time_sender_received in range(max_time, min_time - 1, -1):
                if time_sender_received < 0:
                    break
                self.timing_attack_from_receiver(
                    sender, time_sender_received, remaining_hops - 1, observed_hops + 1, suspected_origins
                )

        return suspected_origins

    def min_hops_to_observe_for_timing_attack(self) -> int:
        return self.config.mixnet.num_mix_layers + 1
