# NomMix Simulation

* [Features](#features)
* [Future Plans](#future-plans)
* [Installation](#installation)
* [Getting Started](#getting-started)

## Features

- Simulate the NomMix protocol with the given parameters.
- Measure the performance of the NomMix protocol.
  - Bandwidth usages
- Analyze the privacy properties that the NomMix protocol provides.
  - Message sizes
  - Node states and hamming distances

## Future Plans

- Simulate more features of the NomMix protocol.
  - Temporal mixing
  - Level-1 noise
- Simulate possible adversarial attacks and measure the robustness of the NomMix protocol.

## Installation

Clone the repository and install the dependencies:
```bash
git clone https://github.com/logos-co/nomos-specs.git
cd nomos-specs
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Getting Started

Copy the [`mixnet/sim/config.ci.yaml`](./config.ci.yaml) file and adjust the parameters to your needs.
Each parameter is explained in the config file.
For more details, please refer to the [documentation](https://www.notion.so/NomMix-Sim-Getting-Started-ee0e2191f4e7437e93976aff2627d7ce?pvs=4).

Run the simulation with the following command:
```bash
python -m mixnet.sim.main --config {config_path}
```

All results are printed in the console as below.
And, all plots are shown once all analysis is done.
```
==========================================
Message Size Distribution
==========================================
   msg_size  count
0      1405  99990

==========================================
Node States of All Nodes over Time
SENDING:-1, IDLE:0, RECEIVING:1
==========================================
        Node-0  Node-1  Node-2  Node-3  Node-4
0            0       0       0       0       0
1            0       0       0       0       0
2            0       0       0       0       0
3            0       0       0       0       0
4            0       0       0       0       0
...        ...     ...     ...     ...     ...
999995       0       0       0       0       0
999996       0       0       0       0       0
999997       0       0       0       0       0
999998       0       0       0       0       0
999999       0       0       0       0       0

[1000000 rows x 5 columns]

Saved DataFrame to all_node_states_2024-07-15T18:20:23.csv

State Counts per Node:
    Node-0  Node-1  Node-2  Node-3  Node-4
 0  970003  970003  970003  970003  970003
 1   19998   19998   19998   19998   19998
-1    9999    9999    9999    9999    9999

Simulation complete!
```

Please note that the result of node state analysis is saved as a CSV file, as printed in the console.
```
Saved DataFrame to all_node_states_2024-07-15T18:20:23.csv
```

If you run the simulation again with the different parameters and want to
compare the results of two simulations,
you can calculate the hamming distance between them:
```bash
python -m mixnet.sim.hamming \
    all_node_states_2024-07-15T18:20:23.csv \
    all_node_states_2024-07-15T19:32:45.csv
```
The output is a floating point number between 0 and 1.
If the output is 0, the results of two simulations are identical.
The closer the result is to 1, the more the two results differ from each other.
```
Hamming distance: 0.29997
```
