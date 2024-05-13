# Mixnet v2 Simulation

## How to run

Make sure that all dependencies specified in the `requirements.txt` in the project root, and run the following command to run the simulation:
```bash
python main.py
```
The following parameters can be configured:
```
usage: main.py [-h] [--running-time RUNNING_TIME] [--num-nodes NUM_NODES] [--num-mix-layers NUM_MIX_LAYERS]

Run simulation

options:
  -h, --help            show this help message and exit
  --running-time RUNNING_TIME
                        Running time of the simulation (default: 30)
  --num-nodes NUM_NODES
                        Number of nodes in the network (default: 2)
  --num-mix-layers NUM_MIX_LAYERS
                        Number of mix layers in the network (default: 2)
```

TODO: Add more details

## Development Status

- [x] Modified Sphinx without encryption
- [x] Naive P2P 1:N broadcasting
- [x] Forwarding messages through mixes, and then broadcasting messages to all nodes
- [x] Naive cover traffic with a constant rate 
- [x] Naive random delays in mix
- [ ] [Adversary simulations](https://www.notion.so/Mixnet-v2-Proof-of-Concept-102d0563e75345a3a6f1c11791fbd746?pvs=4#c5ffa49486ce47ed81d25028bc0d9d40)
- [ ] Reporting & Visualization
- [ ] More realistic P2P broadcasting (e.g. gossipsub)
- [ ] More sophisticated cover traffic (e.g. based on the approximate block interval)
- [ ] More sophisticated mix delays (e.g. Poisson)
- [ ] Modified Sphinx with encryption
