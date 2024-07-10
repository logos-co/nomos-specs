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
    await print_subnet_info(subnets)

    print("Establishing connections...")
    node_list = {}
    all_node_instances = set()
    await establish_connections(subnets, node_list, all_node_instances)

    print("starting executor...")
    exe = Executor.new(7766, node_list)
    await exe.execute(nursery)

    all_nodes = list(all_node_instances)
    checked = []

    await trio.sleep(1)

    print("starting sampling...")
    for _ in range(SAMPLE_THRESHOLD):
        nursery.start_soon(sample_node, exe, subnets, checked)

    print("waiting for sampling to finish...")
    await check_complete(checked)

    print("Test completed")
    shutdown.set()


async def print_subnet_info(subnets):
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


async def establish_connections(subnets, node_list, all_node_instances):
    for subnet in subnets:
        for n in subnets[subnet]:
            this_nodes_peers = n.net_iface().get_peerstore().peer_ids()
            all_node_instances.add(n)
            for i, nn in enumerate(subnets[subnet]):
                if nn.get_id() == n.get_id():
                    continue
                remote_id = nn.get_id().pretty()
                remote_port = nn.get_port()
                addr = "/ip4/127.0.0.1/tcp/{}/p2p/{}/".format(remote_port, remote_id)
                remote_addr = multiaddr.Multiaddr(addr)
                remote = info_from_p2p_addr(remote_addr)
                if subnet not in node_list:
                    node_list[subnet] = []
                node_list[subnet].append(remote)
                if nn.get_id() in this_nodes_peers:
                    continue
                print("{} connecting to {}...".format(n.get_id(), addr))
                await n.net_iface().connect(remote)

    print()


async def check_complete(checked):
    while len(checked) < SAMPLE_THRESHOLD:
        await trio.sleep(0.5)
    print("check_complete exiting")
    return


async def sample_node(exe, subnets, checked):
    s = randint(0, len(subnets) - 1)
    n = randint(0, len(subnets[s]) - 1)
    node = subnets[s][n]
    hashstr = exe.get_hash(s)
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
