import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn

from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run simulation', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--running-time", type=int, default=30, help="Running time of the simulation")
    parser.add_argument("--num-nodes", type=int, default=2, help="Number of nodes in the network")
    parser.add_argument("--num-mix-layers", type=int, default=2, help="Number of mix layers in the network")
    args = parser.parse_args()

    sim = Simulation(args.num_nodes, args.num_mix_layers)
    sim.run(until=args.running_time)

    df = pd.DataFrame(sim.p2p.message_sizes, columns=["message_size"])
    print(df.describe())
    plt.figure(figsize=(10, 6))
    seaborn.boxplot(y=df["message_size"])
    plt.title("Message size distribution")
    plt.ylabel("Message Size (bytes)")
    plt.show()

    print("Simulation complete!")