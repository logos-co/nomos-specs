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
    df = pd.DataFrame([(node.id, cnt) for node, cnt in sim.p2p.nodes_emitted_msg_around_interval.items()], columns=["node", "count"])
    plt.figure(figsize=(10, 6))
    seaborn.barplot(x="node", y="count", data=df)
    plt.title("Messages emitted around the promised interval")
    plt.xlabel("Node ID")
    plt.ylabel("Msg Count")
    plt.show()

    print("Simulation complete!")