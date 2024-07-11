# Data Availability Subnets Proof-Of-Concept

## Contents
This folder contains code as implementation for a Proof-Of-Concept (PoC) for the subnets designed 
to address dispersal and sampling in Data Availability (DA) in Nomos.

Refer to the [Specification](https://www.notion.so/Runnable-DA-PoC-Specification-50f204f2ff0a41d09de4926962bbb4ef?d=9e9677e5536a46d49fe95f366b7c3320#308624c50f1a42769b6c142976999483)
for the details of the design of this PoC.


Being a PoC, this code has no pretentions in terms of quality, and is certainly not meant to reach anywhere near production status.

## How to run 

The entry point is `poc.py` , which can be run with a python3 binary.

It can be parametrized with the following options:

`python poc.py -s 512 -n 64 -t 12 -d 2048`

To understand what these parameter mean, just look at the help output:

```sh
> python poc.py -h
usage: poc.py [-h] [-s SUBNETS] [-n NODES] [-t SAMPLE_THRESHOLD] [-d DATA_SIZE]

options:
  -h, --help            show this help message and exit
  -s SUBNETS, --subnets SUBNETS
                        Number of subnets [default: 256]
  -n NODES, --nodes NODES
                        Number of nodes [default: 32]
  -t SAMPLE_THRESHOLD, --sample-threshold SAMPLE_THRESHOLD
                        Threshold for sampling request attempts [default: 12]
  -d DATA_SIZE, --data-size DATA_SIZE
                        Size of packages [default: 1024]
```


## What it does
The PoC first creates an instance of a light-weight `DANetwork`, which in turn
starts the configured number of nodes.

[!NOTE]
Currently ports are hardcoded. Nodes start at 7561 and are instantiated sequentially from there.
The Executor simulator runs on 8766.

After nodes are up, the subnets are calculated. Subnets calculation is explicitly **not part of the PoC**.
Therefore, the PoC uses a simple strategy of filling all subnets sequentially, and if not enough nodes are requested,
just fills up nodes up to a `REPLICATION_FACTOR` per subnet (thus, each subnet has at least `REPLICATION_FACTOR` nodes).

After nodes are assigned to subnets, the network connections (via direct libp2p links) are established.
Each node in a subnet connects with every other node in that subnet.

Next, the executor is started. It is just a simulator. It creates random data for each subnet of `DATA_SIZE` length,
simulating the columns generated by the NomosDA protocol.

It then establishes one connection per subnet and sends one packet of `DATA_SIZE` length on each of these connections.
The executor also stores a hash of each packet per subnet.

Receiving nodes then forward this package to each of their peers in the subnet.
They also store the respective hash (only).

Finally a simulated check samples up to `SAMPLE_THRESHOLD` nodes. 
For each subnet it simply picks a node randomly and asks if it has the hash.