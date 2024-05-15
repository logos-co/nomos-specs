import argparse

import matplotlib.pyplot as plt
import pandas as pd
import seaborn

from config import Config
from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run simulation', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()

    config = Config.load(args.config)
    sim = Simulation(config)
    sim.run()

    df = pd.DataFrame(sim.p2p.message_sizes, columns=["message_size"])
    print(df.describe())
    plt.figure(figsize=(10, 6))
    seaborn.boxplot(y=df["message_size"])
    plt.title("Message size distribution")
    plt.ylabel("Message Size (bytes)")
    plt.show()

    print("Simulation complete!")