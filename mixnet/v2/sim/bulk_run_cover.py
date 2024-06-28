import argparse
from datetime import datetime

import pandas as pd
from matplotlib import pyplot as plt

from config import P2PConfig, Config
from simulation import Simulation


def bulk_run_cover():
    parser = argparse.ArgumentParser(description="Run simulation",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()
    config = Config.load(args.config)

    results = []

    config.simulation.running_time = 30
    config.mixnet.num_nodes = 1000
    config.mixnet.num_mix_layers = 4
    config.mixnet.payload_size = 320
    config.mixnet.message_interval = 1
    config.mixnet.real_message_prob = 0.01
    config.mixnet.real_message_prob_weights = []
    config.mixnet.max_message_prep_time = 0
    config.mixnet.max_mix_delay = 0
    config.p2p.type = P2PConfig.TYPE_GOSSIP
    config.p2p.connection_density = 6
    config.p2p.max_network_latency = 0.20
    config.measurement.sim_time_per_second = 1

    base = config.mixnet.real_message_prob * 2
    for cover_message_prob in [base, base * 2, base * 3, base * 4, base * 5]:
        config.mixnet.cover_message_prob = cover_message_prob

        sim = Simulation(config)
        sim.run()

        egress, ingress = sim.p2p.measurement.bandwidth()
        results.append({
            "num_nodes": config.mixnet.num_nodes,
            "num_mix_layers": config.mixnet.num_mix_layers,
            "p2p_type": config.p2p.type,
            "real_message_prob": config.mixnet.real_message_prob,
            "cover_message_prob": cover_message_prob,
            "egress_mean": egress.mean(),
            "egress_max": egress.max(),
            "ingress_mean": ingress.mean(),
            "ingress_max": ingress.max(),
        })

    df = pd.DataFrame(results)
    df.to_csv(f"{datetime.now().replace(microsecond=0).isoformat()}.csv", index=False)
    draw_plot(df)


def load_and_plot():
    # with skipping the header
    df = pd.read_csv("2024-05-27T14:14:58.csv")
    print(df)
    draw_plot(df)


def draw_plot(df: pd.DataFrame):
    plt.plot(df["cover_message_prob"], df["egress_mean"], label="Egress Mean", marker="o")
    plt.plot(df["cover_message_prob"], df["egress_max"], label="Egress Max", marker="x")
    plt.plot(df["cover_message_prob"], df["ingress_mean"], label="Ingress Mean", marker="v")
    plt.plot(df["cover_message_prob"], df["ingress_max"], label="Ingress Max", marker="^")

    plt.xlabel("Cover Emission Rate")
    plt.ylabel("Bandwidth (KiB/s)")
    plt.title("Bandwidth vs Cover Emission Rate")
    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    bulk_run_cover()
    # load_and_plot()
