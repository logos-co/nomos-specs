import sys
import asyncio

from network import DANetwork
from subnet import calculate_subnets

default_nodes = 256

if len(sys.argv) == 1:
    nodes = 256
else:
    nodes = int(sys.argv[1])

network = DANetwork(nodes)

async def run_network(net):
    await net.build()

    subnets = calculate_subnets(net.get_nodes())

    print()
    print("By subnets: ")
    for subnet in subnets:
        print("subnet: {} - ".format(subnet), end="")
        for n in subnets[subnet]:
            print(n.hex_id()[:16], end=", ")
        print()
        print()

    print()

    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(run_network(network))
