# Mixnet v2 Simulation

* [How to run](#how-to-run)
* [Mixnet Functionalities](#mixnet-functionalities)
* [Adversary Models](#adversary-models)

## How to run

First, make sure that all dependencies specified in the `requirements.txt` in the project root.
Then, configure parameters in the [`config.yaml`](./config.yaml), and run the following command:
```bash
python main.py --config ./config.yaml
```
The simulation runs during a specified duration, prints the results to the console, and show some plots.

## Mixnet Functionalities
- Modified Sphinx
    - [x] Without encryption
    - [ ] With encryption
- P2P Broadcasting
  - [x] Naive 1:N
  - [ ] More realistic broadcasting (e.g. gossipsub)
- [x] Sending a real message to the mixnet at the promised interval
  - Each node has its own probability of sending a real message at each interval.
- [x] Cover traffic
  - All nodes have the same probability of sending a cover message at each interval.
- [x] Forwarding messages through mixes, and then broadcasting messages to all nodes if the message is real.
- Mix delays
  - [x] Naive random delays
  - [ ] More sophisticated delays (e.g. Poisson) if necessary

## [Adversary Models](https://www.notion.so/Mixnet-v2-Proof-of-Concept-102d0563e75345a3a6f1c11791fbd746?pvs=4#c5ffa49486ce47ed81d25028bc0d9d40)
- [x] Identifying nodes emitting messages around the promised interval.
  - [ ] With partial visibility
- [ ] Correlating senders-receivers based on timing
- [ ] Active attacks
- [ ] Reporting & Visualization
  - With quantifying the effect of attacks above based on parameter changes.