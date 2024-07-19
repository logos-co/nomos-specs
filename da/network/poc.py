import argparse
import sys
import time
from random import randint

import multiaddr
import trio
from constants import *
from executor import Executor
from libp2p.peer.peerinfo import info_from_p2p_addr
from network import DANetwork
from subnet import calculate_subnets

"""
    Entry point for the poc.
    Handles cli arguments, initiates the network
    and waits for it to complete.

    Also does some simple completion check.
"""


async def run_network(params):
    """
    Create the network.
    Run the run_subnets
    """

    num_nodes = int(params.nodes)
    net = DANetwork(num_nodes)
    shutdown = trio.Event()
    disperse_send, disperse_recv = trio.open_memory_channel(0)
    async with trio.open_nursery() as nursery:
        nursery.start_soon(net.build, nursery, shutdown, disperse_send)
        nursery.start_soon(
            run_subnets, net, params, nursery, shutdown, disperse_send, disperse_recv
        )


async def run_subnets(net, params, nursery, shutdown, disperse_send, disperse_recv):
    """
    Run the actual PoC logic.
    Calculate the subnets.
    -> Establish connections based on the subnets <-
    Runs the executor.
    Runs simulated sampling.
    Runs simple completion check
    """

    num_nodes = int(params.nodes)
    num_subnets = int(params.subnets)
    data_size = int(params.data_size)
    sample_threshold = int(params.sample_threshold)
    fault_rate = int(params.fault_rate)
    replication_factor = int(params.replication_factor)

    while len(net.get_nodes()) != num_nodes:
        print("nodes not ready yet")
        await trio.sleep(0.1)

    print("Nodes ready")
    nodes = net.get_nodes()
    subnets = calculate_subnets(nodes, num_subnets, replication_factor)
    await print_subnet_info(subnets)

    print("Establishing connections...")
    node_list = {}
    all_node_instances = set()
    await establish_connections(subnets, node_list, all_node_instances, fault_rate)

    print("Starting executor...")
    exe = Executor.new(EXECUTOR_PORT, node_list, num_subnets, data_size)

    print("Start dispersal and wait to complete...")
    print("depending on network and subnet size this may take a while...")
    global TIMESTAMP
    TIMESTAMP = time.time()
    async with trio.open_nursery() as subnursery:
        subnursery.start_soon(wait_disperse_finished, disperse_recv, num_subnets)
        subnursery.start_soon(exe.disperse, nursery)
        subnursery.start_soon(disperse_watcher, disperse_send.clone())

    print()
    print()

    print("OK. Start sampling...")
    checked = []
    for _ in range(sample_threshold):
        nursery.start_soon(sample_node, exe, subnets, checked)

    print("Waiting for sampling to finish...")
    await check_complete(checked, sample_threshold)

    print_connections(all_node_instances)

    print("Test completed")
    shutdown.set()


TIMESTAMP = time.time()


def print_connections(node_list):
    for n in node_list:
        for p in n.net_iface().get_peerstore().peer_ids():
            if p == n.net_iface().get_id():
                continue
            print("node {} is connected to {}".format(n.get_id(), p))
        print()


async def disperse_watcher(disperse_send):
    while time.time() - TIMESTAMP < 5:
        await trio.sleep(1)

    await disperse_send.send(9999)
    print("canceled")


async def wait_disperse_finished(disperse_recv, num_subnets):
    # run until there are no changes detected
    async for value in disperse_recv:
        if value == 9999:
            print("dispersal finished")
            return

        print(".", end="")

        global TIMESTAMP
        TIMESTAMP = time.time()


async def print_subnet_info(subnets):
    """
    Print which node is in what subnet
    """

    print()
    print("By subnets: ")
    for subnet in subnets:
        print("subnet: {} - ".format(subnet), end="")
        for n in subnets[subnet]:
            print(n.get_id().pretty()[:16], end=", ")
        print()

    print()
    print()


async def establish_connections(subnets, node_list, all_node_instances, fault_rate=0):
    """
    Each node in a subnet connects to the other ones in that subnet.
    """
    for subnet in subnets:
        # n is a DANode
        for n in subnets[subnet]:
            # while nodes connect to each other, they are **mutually** added
            # to their peer lists. Hence, we don't need to establish connections
            # again to peers we are already connected.
            # So in each iteration we get the peer list for the current node
            # to later check if we are already connected with the next peer
            this_nodes_peers = n.net_iface().get_peerstore().peer_ids()
            all_node_instances.add(n)
            faults = []
            for i in range(fault_rate):
                faults.append(randint(0, len(subnets[subnet])))
            for i, nn in enumerate(subnets[subnet]):
                # don't connect to self
                if nn.get_id() == n.get_id():
                    continue
                if i in faults:
                    continue
                remote_id = nn.get_id().pretty()
                remote_port = nn.get_port()
                # this script only works on localhost!
                addr = "/ip4/127.0.0.1/tcp/{}/p2p/{}/".format(remote_port, remote_id)
                remote_addr = multiaddr.Multiaddr(addr)
                remote = info_from_p2p_addr(remote_addr)
                if subnet not in node_list:
                    node_list[subnet] = []
                node_list[subnet].append(remote)
                # check if we are already connected with this peer. If yes, skip connecting
                if nn.get_id() in this_nodes_peers:
                    continue
                if DEBUG:
                    print("{} connecting to {}...".format(n.get_id(), addr))
                await n.net_iface().connect(remote)

    print()


async def check_complete(checked, sample_threshold):
    """
    Simple completion check:
    Check how many nodes have already been "sampled"
    """

    while len(checked) < sample_threshold:
        await trio.sleep(0.5)
    print("check_complete exiting")
    return


async def sample_node(exe, subnets, checked):
    """
    Pick a random subnet.
    Pick a random node in that subnet.
    As the executor has a list of hashes per subnet,
    we can ask that node if it has that hash.
    """

    # s: subnet
    s = randint(0, len(subnets) - 1)
    # n: node (index)
    n = randint(0, len(subnets[s]) - 1)
    # actual node
    node = subnets[s][n]
    # pick the hash to check
    hashstr = exe.get_hash(s)
    # run the "sampling"
    has = await node.has_hash(hashstr)
    if has:
        print("node {} has hash {}".format(node.get_id().pretty(), hashstr))
    else:
        print("node {} does NOT HAVE hash {}".format(node.get_id().pretty(), hashstr))
        print("TEST FAILED")
    # signal we "sampled" another node
    checked.append(1)
    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--subnets", help="Number of subnets [default: 256]")
    parser.add_argument("-n", "--nodes", help="Number of nodes [default: 32]")
    parser.add_argument(
        "-t",
        "--sample-threshold",
        help="Threshold for sampling request attempts [default: 12]",
    )
    parser.add_argument("-d", "--data-size", help="Size of packages [default: 1024]")
    parser.add_argument("-f", "--fault_rate", help="Fault rate [default: 0]")
    parser.add_argument(
        "-r", "--replication_factor", help="Replication factor [default: 4]"
    )
    args = parser.parse_args()

    if not args.subnets:
        args.subnets = DEFAULT_SUBNETS
    if not args.nodes:
        args.nodes = DEFAULT_NODES
    if not args.sample_threshold:
        args.sample_threshold = DEFAULT_SAMPLE_THRESHOLD
    if not args.data_size:
        args.data_size = DEFAULT_DATA_SIZE
    if not args.replication_factor:
        args.replication_factor = DEFAULT_REPLICATION_FACTOR
    if not args.fault_rate:
        args.fault_rate = 0

    print("Number of subnets will be: {}".format(args.subnets))
    print("Number of nodes will be: {}".format(args.nodes))
    print("Size of data package will be: {}".format(args.data_size))
    print("Threshold for sampling attempts will be: {}".format(args.sample_threshold))
    print("Fault rate will be: {}".format(args.fault_rate))

    print()
    print("*******************")
    print("Starting network...")

    trio.run(run_network, args)
