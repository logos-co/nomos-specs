import sys
from random import randint

import multiaddr
import trio
from constants import *
from executor import Executor
from libp2p.peer.peerinfo import info_from_p2p_addr
from network import DANetwork
from subnet import calculate_subnets

default_nodes = 32


async def run_network():
    if len(sys.argv) == 1:
        num_nodes = default_nodes
    else:
        num_nodes = int(sys.argv[1])

    net = DANetwork(num_nodes)
    shutdown = trio.Event()
    async with trio.open_nursery() as nursery:
        nursery.start_soon(net.build, nursery, shutdown)
        nursery.start_soon(run_subnets, net, num_nodes, nursery, shutdown)


async def run_subnets(net, num_nodes, nursery, shutdown):
    while len(net.get_nodes()) != num_nodes:
        print("nodes not ready yet")
        await trio.sleep(0.1)

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

    node_list = []
    all_node_instances = set()

    for subnet in subnets:
        for n in subnets[subnet]:
            all_node_instances.add(n)
            for i, nn in enumerate(subnets[subnet]):
                if nn.get_id() == n.get_id():
                    continue
                remote_id = nn.get_id().pretty()
                remote_port = nn.get_port()
                addr = "/ip4/127.0.0.1/tcp/{}/p2p/{}/".format(remote_port, remote_id)
                remote_addr = multiaddr.Multiaddr(addr)
                print("{} connecting to {}...".format(n.get_id(), addr))
                remote = info_from_p2p_addr(remote_addr)
                if i == 0:
                    node_list.append(remote)
                await n.net_iface().connect(remote)

    print()
    print("starting executor...")
    exe = Executor.new(7766, node_list)
    await exe.execute(nursery)

    all_nodes = list(all_node_instances)
    checked = []

    print("starting sampling...")
    for _ in range(SAMPLE_THRESHOLD):
        nursery.start_soon(sample_node, exe, all_nodes, checked)

    print("waiting for sampling to finish...")
    await check_complete(checked)

    print("Test completed")
    shutdown.set()


async def check_complete(checked):
    while len(checked) < SAMPLE_THRESHOLD:
        await trio.sleep(0.5)
        print(len(checked))
        print("waited")
    print("check_complete exiting")
    return


async def sample_node(exe, all_nodes, checked):
    r = randint(0, COL_SIZE - 1)
    hashstr = exe.get_hash(r)
    n = randint(0, len(all_nodes) - 1)
    node = all_nodes[n]
    has = await node.has_hash(hashstr)
    if has:
        print("node {} has hash {}".format(node.get_id().pretty(), hashstr))
    else:
        print("node {} does NOT HAVE hash {}".format(node.get_id().pretty(), hashstr))
        print("TEST FAILED")
    checked.append(1)
    return


if __name__ == "__main__":
    trio.run(run_network)
