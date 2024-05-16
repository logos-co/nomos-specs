import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn

from config import Config
from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run simulation", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()

    config = Config.load(args.config)
    sim = Simulation(config)
    sim.run()

    # Stat the distribution of message sizes
    df = pd.DataFrame(sim.p2p.message_sizes, columns=["message_size"])
    print(df.describe())

    # Visualize the nodes emitted messages around the promised interval
    df = pd.DataFrame(
        [(node.id, cnt, node.id < len(config.real_message_prob_weights))
         for node, cnt in sim.p2p.senders_around_interval.items()],
        columns=["NodeID", "MsgCount", "Expected"]
    )
    plt.figure(figsize=(10, 6))
    seaborn.barplot(data=df, x="NodeID", y="MsgCount", hue="Expected", palette={True: "red", False: "blue"})
    plt.title("Messages emitted around the promised interval")
    plt.xlabel("Sender Node ID")
    plt.ylabel("Msg Count")
    plt.legend(title="Expected")
    plt.show()

    # Analyze the number of mixed messages per node per observation window
    dataframes = []
    for mixed_msgs_per_node in sim.p2p.mixed_msgs_per_window:
        df = pd.DataFrame([(node.id, cnt) for node, cnt in mixed_msgs_per_node.items()], columns=["NodeID", "MsgCount"])
        dataframes.append(df)
    observation_times = range(len(dataframes))
    df = pd.concat([df.assign(Time=time) for df, time in zip(dataframes, observation_times)], ignore_index=True)
    df = df.pivot(index="Time", columns="NodeID", values="MsgCount")
    plt.figure(figsize=(12, 6))
    for column in df.columns:
        plt.plot(df.index, df[column], marker='o', label=column)
    plt.title('Mixed messages in each mix over time')
    plt.xlabel('Time')
    plt.ylabel('Msg Count')
    plt.legend(title='Node ID')
    plt.grid(True)
    plt.show()

    print("Simulation complete!")