from random import randint

from constants import *


def calculate_subnets(node_list, num_subnets, replication_factor):
    """
    Calculate in which subnet(s) to place each node.
    This PoC does NOT require this to be analyzed,
    nor to find the best solution.

    Hence, we just use a simple model here:

    1. Iterate all nodes and place each node in the subsequent subnet
    2. If the subnet list can not be filled, start again from the top of the list
    3. If each subnet does NOT have at least up to REPLICATION_FACTOR nodes, then
       fill up the list with nodes up to the factor.

    NOTE: This might be incomplete and/or buggy, but should be sufficient for
    the purpose of the PoC.

    If however, you find a bug, please report.

    """
    # key of dict is the subnet number
    subnets = {}
    for i, n in enumerate(node_list):
        idx = i % num_subnets

        # each key has an array, so multiple nodes can be filter
        # into a subnet
        if idx not in subnets:
            subnets[idx] = []
        subnets[idx].append(n)

    listlen = len(node_list)
    i = listlen
    # if there are less nodes than subnets
    while i < num_subnets:
        subnets[i] = []
        subnets[i].append(node_list[i % listlen])
        i += 1

    # if not each subnet has at least factor number of nodes, fill up
    if listlen < replication_factor * num_subnets:
        for subnet in subnets:
            last = subnets[subnet][len(subnets[subnet]) - 1].get_id()
            idx = -1
            # what is the last filled index of a subnet row
            for j, n in enumerate(node_list):
                if n.get_id() == last:
                    idx = j + 1
            # fill up until factor
            while len(subnets[subnet]) < replication_factor:
                # wrap index if at end
                if idx > len(node_list) - 1:
                    idx = 0
                # don't add same node multiple times
                if node_list[idx] in subnets[subnet]:
                    idx += 1
                    continue
                subnets[subnet].append(node_list[idx])
                idx += 1

    return subnets
