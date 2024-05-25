import argparse
from datetime import datetime

import pandas as pd
from matplotlib import pyplot as plt

from config import P2PConfig, Config
from simulation import Simulation

# https://matplotlib.org/stable/api/markers_api.html
MARKERS = ['o', 'x', 'v', '^', '<', '>']
NUM_NODES_SET = [10, 200, 400, 600, 800, 1000]
NUM_MIX_LAYERS_SET = [0, 2, 4]


def bulk_run():
    parser = argparse.ArgumentParser(description="Run simulation",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()
    config = Config.load(args.config)

    results = []

    for num_nodes in NUM_NODES_SET:
        config.mixnet.num_nodes = num_nodes

        for p2p_type in [P2PConfig.TYPE_GOSSIP]:
            config.p2p.type = p2p_type

            for num_mix_layers in NUM_MIX_LAYERS_SET:
                config.mixnet.num_mix_layers = num_mix_layers

                for cover_message_prob in [0.0, config.mixnet.real_message_prob * 2]:
                    config.mixnet.cover_message_prob = cover_message_prob

                    sim = Simulation(config)
                    sim.run()

                    ingress, egress = sim.p2p.measurement.bandwidth()
                    results.append({
                        "num_nodes": num_nodes,
                        "config": f"{p2p_type}: {num_mix_layers}: {cover_message_prob}",
                        "ingress_mean": ingress.mean(),
                        "ingress_max": ingress.max(),
                        "egress_mean": egress.mean(),
                        "egress_max": egress.max(),
                    })

    df = pd.DataFrame(results)
    df.to_csv(f"{datetime.now().replace(microsecond=0).isoformat()}.csv", index=False)
    plot(df)


def load_and_plot():
    # with skipping the header
    df = pd.read_csv("2024-05-25T23:16:39.csv")
    print(df)
    plot(df)


def plot(df: pd.DataFrame):
    ingress_max_df = df.pivot(index='num_nodes', columns='config', values='ingress_max')
    plt.figure(figsize=(12, 6))
    fig, ax = plt.subplots()
    for config in ingress_max_df.columns:
        num_mix_layers = int(config.split(":")[1].strip())
        ax.plot(ingress_max_df.index, ingress_max_df[config], label=config,
                marker=MARKERS[NUM_MIX_LAYERS_SET.index(num_mix_layers)])
    plt.title("Ingress Bandwidth (Max)")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Max Bandwidth (KiB/s)")
    plt.legend(title="mode: layers: cover", loc="upper left")
    plt.tight_layout()
    plt.grid(True)
    plt.show()
    ingress_max_y_lim = ax.get_ylim()

    ingress_mean_df = df.pivot(index='num_nodes', columns='config', values='ingress_mean')
    plt.figure(figsize=(12, 6))
    fig, ax = plt.subplots()
    for config in ingress_mean_df.columns:
        num_mix_layers = int(config.split(":")[1].strip())
        ax.plot(ingress_mean_df.index, ingress_mean_df[config], label=config,
                marker=MARKERS[NUM_MIX_LAYERS_SET.index(num_mix_layers)])
    plt.title("Ingress Bandwidth (Mean)")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Mean Bandwidth (KiB/s)")
    plt.legend(title="mode: layers: cover", loc="upper left")
    plt.tight_layout()
    plt.grid(True)
    ax.set_ylim(ingress_max_y_lim)
    plt.show()

    egress_max_df = df.pivot(index='num_nodes', columns='config', values='egress_max')
    plt.figure(figsize=(12, 6))
    fig, ax = plt.subplots()
    for config in egress_max_df.columns:
        num_mix_layers = int(config.split(":")[1].strip())
        ax.plot(egress_max_df.index, egress_max_df[config], label=config,
                marker=MARKERS[NUM_MIX_LAYERS_SET.index(num_mix_layers)])
    plt.title("Egress Bandwidth (Max)")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Max Bandwidth (KiB/s)")
    plt.legend(title="mode: layers: cover", loc="upper left")
    plt.tight_layout()
    plt.grid(True)
    plt.show()
    ingress_max_y_lim = ax.get_ylim()

    egress_mean_df = df.pivot(index='num_nodes', columns='config', values='egress_mean')
    plt.figure(figsize=(12, 6))
    fig, ax = plt.subplots()
    for config in egress_mean_df.columns:
        num_mix_layers = int(config.split(":")[1].strip())
        ax.plot(egress_mean_df.index, egress_mean_df[config], label=config,
                marker=MARKERS[NUM_MIX_LAYERS_SET.index(num_mix_layers)])
    plt.title("Egress Bandwidth (Mean)")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Mean Bandwidth (KiB/s)")
    plt.legend(title="mode: layers: cover", loc="upper left")
    plt.tight_layout()
    plt.grid(True)
    ax.set_ylim(ingress_max_y_lim)
    plt.show()


if __name__ == "__main__":
    bulk_run()
    # load_and_plot()
