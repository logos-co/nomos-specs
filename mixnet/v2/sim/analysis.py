import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from adversary import NodeState
from simulation import Simulation


class Analysis:
    def __init__(self, sim: Simulation):
        self.sim = sim

    def run(self):
        self.bandwidth()
        self.message_size_distribution()
        self.messages_emitted_around_interval()
        self.mixed_messages_per_node_over_time()
        self.node_states()

    def bandwidth(self):
        dataframes = []
        for ingress_bandwidths, egress_bandwidths in zip(self.sim.p2p.measurement.ingress_bandwidth_per_time, self.sim.p2p.measurement.egress_bandwidth_per_time):
            rows = []
            for node in self.sim.p2p.nodes:
                rows.append((node.id, ingress_bandwidths[node]/1024.0, egress_bandwidths[node]/1024.0))
            df = pd.DataFrame(rows, columns=["node_id", "ingress", "egress"])
            dataframes.append(df)
        times = range(len(dataframes))
        df = pd.concat([df.assign(Time=time) for df, time in zip(dataframes, times)], ignore_index=True)
        df = df.pivot(index="Time", columns="node_id", values=["ingress", "egress"])
        plt.figure(figsize=(12, 6))
        for column in df.columns:
            marker = "x" if column[0] == "ingress" else "o"
            plt.plot(df.index, df[column], marker=marker, label=column[0])
        plt.title("Ingress/egress bandwidth of each node over time")
        plt.xlabel("Time")
        plt.ylabel("Bandwidth (KiB/s)")
        plt.ylim(bottom=0)
        # Customize the legend to show only 'ingress' and 'egress' regardless of node_id
        handles, labels = plt.gca().get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        plt.legend(by_label.values(), by_label.keys())
        plt.grid(True)
        plt.show()

    def message_size_distribution(self):
        df = pd.DataFrame(self.sim.p2p.adversary.message_sizes, columns=["message_size"])
        print(df.describe())

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

    def mixed_messages_per_node_over_time(self):
        dataframes = []
        for mixed_msgs_per_node in self.sim.p2p.adversary.mixed_msgs_per_window:
            df = pd.DataFrame([(node.id, cnt) for node, cnt in mixed_msgs_per_node.items()],
                              columns=["node_id", "msg_count"])
            dataframes.append(df)
        observation_times = range(len(dataframes))
        df = pd.concat([df.assign(Time=time) for df, time in zip(dataframes, observation_times)], ignore_index=True)
        df = df.pivot(index="Time", columns="node_id", values="msg_count")
        plt.figure(figsize=(12, 6))
        for column in df.columns:
            plt.plot(df.index, df[column], marker="o", label=column)
        plt.title("Mixed messages in each mix over time")
        plt.xlabel("Time")
        plt.ylabel("Msg Count")
        plt.ylim(bottom=0)
        plt.legend(title="Node ID")
        plt.grid(True)
        plt.show()

    def node_states(self):
        rows = []
        for time, node_states in self.sim.p2p.adversary.node_states.items():
            for node, state in node_states.items():
                rows.append((time, node.id, state))
        df = pd.DataFrame(rows, columns=["time", "node_id", "state"])

        plt.figure(figsize=(10, 6))
        seaborn.scatterplot(data=df, x="time", y="node_id", hue="state", palette={NodeState.SENDING: "red", NodeState.RECEIVING: "blue"})
        plt.title("Node states over time")
        plt.xlabel("Time")
        plt.ylabel("Node ID")
        plt.legend(title="state")
        plt.show()

