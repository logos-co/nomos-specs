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

- Modified Sphinx
    - [x] Without encryption
    - [ ] With encryption
- P2P Broadcasting
  - [x] Naive 1:N
  - [ ] More realistic broadcasting (e.g. gossipsub)
- [x] Forwarding messages through mixes, and then broadcasting messages to all nodes
- Cover traffic
  - [x] With a constant rate 
  - [ ] More sophisticated rate (e.g. based on the approximate block interval)
- Mix delays
  - [x] Naive random delays
  - [ ] More sophisticated delays (e.g. Poisson)
- [Adversary simulations](https://www.notion.so/Mixnet-v2-Proof-of-Concept-102d0563e75345a3a6f1c11791fbd746?pvs=4#c5ffa49486ce47ed81d25028bc0d9d40)
  - [ ] Observing message emission patterns
  - [ ] Correlating senders-receivers based on timing
  - [ ] Active attacks
  - [ ] Reporting & Visualization