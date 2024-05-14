# Mixnet v2 Simulation

## How to run

First, make sure that all dependencies specified in the `requirements.txt` in the project root.
Then, configure parameters in the [config.yaml](./config.yaml), and run the following command:
```bash
python main.py --config ./config.yaml
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