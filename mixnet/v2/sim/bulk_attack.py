import argparse
from datetime import datetime

import pandas as pd
from matplotlib import pyplot as plt

from analysis import Analysis
from config import Config, P2PConfig
from simulation import Simulation


def bulk_attack():
    parser = argparse.ArgumentParser(description="Run multiple passive adversary attack simulations",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()
    config = Config.load(args.config)

    config.simulation.running_time = 300
    config.mixnet.num_nodes = 100
    config.mixnet.payload_size = 320
    config.mixnet.message_interval = 10
    config.mixnet.real_message_prob = 0.01
    config.mixnet.real_message_prob_weights = []
    config.mixnet.max_message_prep_time = 0
    config.p2p.connection_density = 6
    config.p2p.min_network_latency = 1
    config.p2p.max_network_latency = 1
    config.measurement.sim_time_per_second = 10

    results = []

    for p2p_type in [P2PConfig.TYPE_ONE_TO_ALL, P2PConfig.TYPE_GOSSIP]:
        config.p2p.type = p2p_type

        for num_mix_layers in [0, 1, 2, 3, 4]:
            config.mixnet.num_mix_layers = num_mix_layers

            for cover_message_prob in [0.0, 0.1, 0.2, 0.3, 0.4]:
                config.mixnet.cover_message_prob = cover_message_prob

                for mix_delay in [0]:
                    config.mixnet.min_mix_delay = mix_delay
                    config.mixnet.max_mix_delay = mix_delay

                    sim = Simulation(config)
                    sim.run()

                    analysis = Analysis(sim, config, show_plots=False)
                    precision, recall, f1_score = analysis.messages_emitted_around_interval()
                    print(
                        f"ANALYZING TIMING ATTACK: p2p_type:{p2p_type}, {num_mix_layers} layers, {cover_message_prob} cover, {mix_delay} delay")
                    timing_attack_df = analysis.timing_attack(analysis.message_hops())

                    results.append({
                        "p2p_type": p2p_type,
                        "num_mix_layers": num_mix_layers,
                        "cover_message_prob": cover_message_prob,
                        "mix_delay": mix_delay,
                        "global_precision": precision,
                        "global_recall": recall,
                        "global_f1_score": f1_score,
                        "target_median": float(timing_attack_df.median().iloc[0]),
                        "target_std": float(timing_attack_df.std().iloc[0]),
                        "target_min": float(timing_attack_df.min().iloc[0]),
                        "target_25%": float(timing_attack_df.quantile(0.25).iloc[0]),
                        "target_mean": float(timing_attack_df.mean().iloc[0]),
                        "target_75%": float(timing_attack_df.quantile(0.75).iloc[0]),
                        "target_max": float(timing_attack_df.max().iloc[0]),
                    })

    df = pd.DataFrame(results)
    df.to_csv(f"bulk-attack-{datetime.now().replace(microsecond=0).isoformat()}.csv", index=False)
    plot_global_metrics(df)
    plot_target_metrics(df)


def plot_global_metrics(df: pd.DataFrame):
    for p2p_type in df["p2p_type"].unique():
        # Plotting global precision, recall, and f1 score against different parameters
        fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 15))

        # Precision plot
        for cover_message_prob in df["cover_message_prob"].unique():
            subset = df[(df["cover_message_prob"] == cover_message_prob) & (df["p2p_type"] == p2p_type)]
            axes[0].plot(subset["num_mix_layers"], subset["global_precision"], label=f"{cover_message_prob} cover rate")
        axes[0].set_title(f"Global Precision ({p2p_type})")
        axes[0].set_xlabel("# of Mix Layers")
        axes[0].set_ylabel("Global Precision (%)")
        axes[0].set_ylim(0, 100)
        axes[0].legend()

        # Recall plot
        for cover_message_prob in df["cover_message_prob"].unique():
            subset = df[(df["cover_message_prob"] == cover_message_prob) & (df["p2p_type"] == p2p_type)]
            axes[1].plot(subset["num_mix_layers"], subset["global_recall"], label=f"{cover_message_prob} cover rate")
        axes[1].set_title(f"Global Recall ({p2p_type})")
        axes[1].set_xlabel("# of Mix Layers")
        axes[1].set_ylabel("Global Recall (%)")
        axes[1].set_ylim(0, 100)
        axes[1].legend()

        # F1 Score plot
        for cover_message_prob in df["cover_message_prob"].unique():
            subset = df[(df["cover_message_prob"] == cover_message_prob) & (df["p2p_type"] == p2p_type)]
            axes[2].plot(subset["num_mix_layers"], subset["global_f1_score"], label=f"{cover_message_prob} cover rate")
        axes[2].set_title(f"Global F1 Score ({p2p_type})")
        axes[2].set_xlabel("# of Mix Layers")
        axes[2].set_ylabel("Global F1 Score (%)")
        axes[2].set_ylim(0, 100)
        axes[2].legend()

        plt.tight_layout()
        plt.show()


def plot_target_metrics(df: pd.DataFrame):
    for p2p_type in df["p2p_type"].unique():
        plt.figure(figsize=(12, 6))
        for cover_message_prob in df["cover_message_prob"].unique():
            subset = df[(df["cover_message_prob"] == cover_message_prob) & (df["p2p_type"] == p2p_type)]
            plt.plot(subset["num_mix_layers"], subset["target_median"], label=f"{cover_message_prob} cover rate")
        plt.title(f"Timing Attack Success Rate ({p2p_type})")
        plt.xlabel("# of Mix Layers")
        plt.ylabel("Median of Success Rates (%)")
        plt.ylim(0, 100)
        plt.legend()
        plt.tight_layout()
        plt.show()


if __name__ == "__main__":
    bulk_attack()
