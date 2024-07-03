import argparse
import asyncio

from mixnet.sim.config import Config
from mixnet.sim.simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run mixnet simulation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config", type=str, required=True, help="Configuration file path"
    )
    args = parser.parse_args()

    config = Config.load(args.config)
    sim = Simulation(config)
    asyncio.run(sim.run())

    print("Simulation complete!")
