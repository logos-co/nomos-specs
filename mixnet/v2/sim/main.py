import argparse

from simulation import Simulation

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run simulation', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--running-time", type=int, default=30, help="Running time of the simulation")
    parser.add_argument("--num-nodes", type=int, default=2, help="Number of nodes in the network")
    parser.add_argument("--num-mix-layers", type=int, default=2, help="Number of mix layers in the network")
    args = parser.parse_args()

    sim = Simulation(args.num_nodes, args.num_mix_layers)
    sim.run(until=args.running_time)
    print("Simulation complete!")