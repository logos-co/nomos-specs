import argparse

from config import Config
from analysis import Analysis
from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run simulation", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--config", type=str, required=True, help="Configuration file path")
    args = parser.parse_args()

    config = Config.load(args.config)
    sim = Simulation(config)
    sim.run()

    Analysis(sim, config).run()

    print("Simulation complete!")