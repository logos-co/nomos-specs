import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn

from node import Node
from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run simulation', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--running-time", type=int, default=30, help="Running time of the simulation")
    parser.add_argument("--num-nodes", type=int, default=2, help="Number of nodes in the network")
    parser.add_argument("--num-mix-layers", type=int, default=2, help="Number of mix layers in the network")
    parser.add_argument("--message-interval", type=int, default=1, help="Message emission interval")
    parser.add_argument("--message-prob", type=float, default=0.2, help="Message emission probability per interval")
    parser.add_argument("--max-message-prep-time", type=float, default=0.3, help="Max preparation time before sending a message")
    args = parser.parse_args()

    node_params = Node.Parameters(args.num_mix_layers, args.message_interval, args.message_prob, args.max_message_prep_time)

    sim = Simulation(args.num_nodes, node_params)
    sim.run(until=args.running_time)

    df = pd.DataFrame(sim.p2p.message_sizes, columns=["message_size"])
    print(df.describe())
    plt.figure(figsize=(10, 6))
    seaborn.boxplot(y=df["message_size"])
    plt.title("Message size distribution")
    plt.ylabel("Message Size (bytes)")
    plt.show()

    print("Simulation complete!")