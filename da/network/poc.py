import sys
import trio
import multiaddr

from network import DANetwork
from subnet import calculate_subnets

from libp2p.peer.peerinfo import (
    info_from_p2p_addr,
)


default_nodes = 32 

async def run_network():
    if len(sys.argv) == 1:
        num_nodes = default_nodes 
    else:
        num_nodes = int(sys.argv[1])

    net = DANetwork(num_nodes)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(net.build, nursery)
        nursery.start_soon(run_subnets,net, num_nodes)
    
    await trio.sleep_forever()


async def run_subnets(net, num_nodes):
    while len(net.get_nodes()) != num_nodes:
        print("nodes not ready yet")
        await trio.sleep(1)

    print("nodes ready")
    nodes = net.get_nodes()
    subnets = calculate_subnets(nodes)

    print()
    print("By subnets: ")
    for subnet in subnets:
        print("subnet: {} - ".format(subnet), end="")
        for n in subnets[subnet]:
            print(n.get_id().pretty()[:16], end=", ")
        print()
        print()

    print()

    print()
    print("Establishing connections...")

    for subnet in subnets:
        for n in subnets[subnet]:
            for nn in subnets[subnet]:
                if nn.get_id() == n.get_id():
                    continue
                remote_id = nn.get_id().pretty()
                remote_port = nn.get_port()
                addr = "/ip4/127.0.0.1/tcp/{}/p2p/{}/".format(remote_port,remote_id)
                remote_addr = multiaddr.Multiaddr(addr)
                print("{} connecting to {}...".format(n.get_id(), addr))
                remote = info_from_p2p_addr(remote_addr)
                await n.net_iface().connect(remote)

    print()

if __name__ == "__main__":
    trio.run(run_network)
