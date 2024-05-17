import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from simulation import Simulation


class Analysis:
    def __init__(self, sim: Simulation):
        self.sim = sim

    def run(self):
        self.message_size_distribution()
        self.messages_emitted_around_interval()
        self.mixed_messages_per_node_over_time()

    def message_size_distribution(self):
        df = pd.DataFrame(self.sim.p2p.adversary.message_sizes, columns=["message_size"])
        print(df.describe())

    def messages_emitted_around_interval(self):
        df = pd.DataFrame(
            [(node.id, cnt, node.id < len(self.sim.config.real_message_prob_weights))
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
        plt.legend(title="Node ID")
        plt.grid(True)
        plt.show()
