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

                    egress, ingress = sim.p2p.measurement.bandwidth()
                    results.append({
                        "num_nodes": num_nodes,
                        "config": f"{p2p_type}: {num_mix_layers}: {cover_message_prob}",
                        "egress_mean": egress.mean(),
                        "egress_max": egress.max(),
                        "ingress_mean": ingress.mean(),
                        "ingress_max": ingress.max(),
                    })

    df = pd.DataFrame(results)
    df.to_csv(f"{datetime.now().replace(microsecond=0).isoformat()}.csv", index=False)
    draw_plots(df)


def load_and_plot():
    # with skipping the header
    df = pd.read_csv("2024-05-25T23:16:39.csv")
    print(df)
    draw_plots(df)


def draw_plots(df: pd.DataFrame):
    max_ylim = draw_plot(df, "num_nodes", "config", "egress_max", "Egress Bandwidth (Max)",
                                "Number of Nodes", "Max Bandwidth (KiB/s)")
    draw_plot(df, "num_nodes", "config", "egress_mean", "Egress Bandwidth (Mean)",
              "Number of Nodes", "Mean Bandwidth (KiB/s)", max_ylim)

    max_ylim = draw_plot(df, "num_nodes", "config", "ingress_max", "Ingress Bandwidth (Max)",
                         "Number of Nodes", "Max Bandwidth (KiB/s)")
    draw_plot(df, "num_nodes", "config", "ingress_mean", "Ingress Bandwidth (Mean)",
              "Number of Nodes", "Mean Bandwidth (KiB/s)", max_ylim)


def draw_plot(df: pd.DataFrame, index: str, column: str, value: str, title: str, xlabel: str, ylabel: str,
              ylim: float = None) -> float:
    df_pivot = df.pivot(index=index, columns=column, values=value)
    plt.figure(figsize=(12, 6))
    fig, ax = plt.subplots()
    for i, config in enumerate(df_pivot.columns):
        marker = MARKERS[NUM_MIX_LAYERS_SET.index(int(config.split(":")[1].strip()))]
        ax.plot(df_pivot.index, df_pivot[config], label=config, marker=marker)
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.legend(title="mode: layers: cover", loc="upper left")
    plt.tight_layout()
    plt.grid(True)
    if ylim is not None:
        ax.set_ylim(ylim)
    plt.show()
    return ax.get_ylim()


if __name__ == "__main__":
    # bulk_run()
    load_and_plot()
