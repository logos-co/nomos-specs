import argparse

import pandas as pd
import seaborn
from matplotlib import pyplot as plt

from config import P2PConfig, Config
from analysis import Analysis
from simulation import Simulation

COL_P2P_TYPE = "P2P Type"
COL_NUM_NODES = "Num Nodes"
COL_TRAFFIC_TYPE = "Traffic Type"
COL_STAT = "Stat"
COL_BANDWIDTH = "Bandwidth"

TRAFFIC_TYPE_INGRESS = "Ingress"
TRAFFIC_TYPE_EGRESS = "Egress"
STAT_MEAN = "mean"
STAT_MAX = "max"


def bulk_run():
    parser = argparse.ArgumentParser(description="Run simulation",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()
    config = Config.load(args.config)

    data = {
        COL_P2P_TYPE: [],
        COL_NUM_NODES: [],
        COL_TRAFFIC_TYPE: [],
        COL_STAT: [],
        COL_BANDWIDTH: [],
    }

    message_size_df = None

    for p2p_type in [P2PConfig.TYPE_ONE_TO_ALL, P2PConfig.TYPE_GOSSIP]:
        config.p2p.type = p2p_type

        num_nodes_list = [10, 100, 1000]
        for i, num_nodes in enumerate(num_nodes_list):
            config.mixnet.num_nodes = num_nodes
            sim = Simulation(config)
            sim.run()

            if message_size_df is None:
                message_size_df = Analysis(sim, config).message_size_distribution()

            if i == len(num_nodes_list) - 1:
                Analysis(sim, config).run()

            nonzero_ingresses, nonzero_egresses = [], []
            for ingress_bandwidths, egress_bandwidths in zip(sim.p2p.measurement.ingress_bandwidth_per_time,
                                                             sim.p2p.measurement.egress_bandwidth_per_time):
                for node in sim.p2p.nodes:
                    ingress = ingress_bandwidths[node] / 1024.0
                    egress = egress_bandwidths[node] / 1024.0
                    if ingress > 0:
                        nonzero_ingresses.append(ingress)
                    if egress > 0:
                        nonzero_egresses.append(egress)

            ingresses = pd.Series(nonzero_ingresses)
            add_data(data, p2p_type, num_nodes, TRAFFIC_TYPE_INGRESS, STAT_MEAN, ingresses.mean())
            add_data(data, p2p_type, num_nodes, TRAFFIC_TYPE_INGRESS, STAT_MAX, ingresses.max())
            egresses = pd.Series(nonzero_egresses)
            add_data(data, p2p_type, num_nodes, TRAFFIC_TYPE_EGRESS, STAT_MEAN, egresses.mean())
            add_data(data, p2p_type, num_nodes, TRAFFIC_TYPE_EGRESS, STAT_MAX, egresses.max())

    df = pd.DataFrame(data)
    draw_bandwidth_plot(df, TRAFFIC_TYPE_INGRESS, config, message_size_df)
    draw_bandwidth_plot(df, TRAFFIC_TYPE_EGRESS, config, message_size_df)


def add_data(data: dict, p2p_type: str, num_nodes: int, bandwidth_type: str, stat: str, bandwidth: float):
    data[COL_P2P_TYPE].append(p2p_type)
    data[COL_NUM_NODES].append(num_nodes)
    data[COL_TRAFFIC_TYPE].append(bandwidth_type)
    data[COL_STAT].append(stat)
    data[COL_BANDWIDTH].append(bandwidth)


def draw_bandwidth_plot(df: pd.DataFrame, traffic_type: str, config: Config, message_size_df: pd.DataFrame):
    ingress_df = df[df[COL_TRAFFIC_TYPE] == traffic_type]

    plt.figure(figsize=(12, 6))

    mean_df = ingress_df[ingress_df[COL_STAT] == STAT_MEAN]
    seaborn.barplot(data=mean_df, x=COL_NUM_NODES, y=COL_BANDWIDTH, hue=COL_P2P_TYPE, ax=plt.gca(), capsize=0.1)
    max_df = ingress_df[ingress_df[COL_STAT] == STAT_MAX]
    barplot = seaborn.barplot(data=max_df, x=COL_NUM_NODES, y=COL_BANDWIDTH, hue=COL_P2P_TYPE, ax=plt.gca(),
                              capsize=0.1, alpha=0.5)

    # Adding labels to each bar
    for p in barplot.patches:
        height = p.get_height()
        if height > 0:  # Only label bars with positive height
            barplot.annotate(format(height, ".2f"),
                             (p.get_x() + p.get_width() / 2., height),
                             ha="center", va="center",
                             xytext=(0, 9),
                             textcoords="offset points")

    plt.title(f"{traffic_type} Bandwidth")
    plt.xlabel(COL_NUM_NODES)
    plt.ylabel(f"{COL_BANDWIDTH} (KB/s)")

    # Custom legend to show Mean and Max
    handles, labels = barplot.get_legend_handles_labels()
    for i in range(len(labels) // 2):
        labels[i] = labels[i] + f" ({STAT_MEAN})"
    for i in range(len(labels) // 2, len(labels)):
        labels[i] = labels[i] + f" ({STAT_MAX})"
    plt.legend(handles=handles, labels=labels, loc="upper left")

    desc = (
        f"message: {message_size_df["message_size"].mean():.0f} bytes\n"
        f"{config.description()}"
    )
    plt.text(1.02, 0.5, desc, transform=plt.gca().transAxes, verticalalignment="center", fontsize=12)
    plt.subplots_adjust(right=0.8)  # Adjust layout to make room for the text

    plt.show()


if __name__ == "__main__":
    bulk_run()
