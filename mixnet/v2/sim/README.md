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