from math import ceil, floor
from typing import List
from unittest import TestCase
from .subnetwork_assignment import (
    generate_distribution_set,
    generate_distribution_set_v3,
    calculate_minimum_membership
)
from hashlib import blake2b, sha512
from uuid import uuid4
from itertools import chain


SUBNETWORK_SIZE: int = 4096
NODES_OVER_NETWORK_SIZE: List[float] = [0.1, 0.25, 0.5, 0.75, 1.0, 2.0, 10.0]
HASHERS = [lambda x: sha512(x).digest()]


class TestSubnetworkAssignment(TestCase):
    def test_no_subnetwork_empty(self):
        for hasher in HASHERS:
            for nodes_factor in reversed(NODES_OVER_NETWORK_SIZE):
                total_nodes = int(SUBNETWORK_SIZE * nodes_factor)
                nodes = [uuid4() for _ in range(total_nodes)]
                replication_factor = ceil(5/nodes_factor)
                minimum_membership = calculate_minimum_membership(SUBNETWORK_SIZE, total_nodes, replication_factor)
                subsets = set(
                    chain.from_iterable(
                        generate_distribution_set(
                            blake2b(_id.bytes).digest(),
                            minimum_membership,
                            SUBNETWORK_SIZE,
                            hasher=hasher
                        )
                        for _id in nodes
                    )
                )
                print(f"Total nodes: {total_nodes}")
                self.assertGreater(len(subsets), floor(SUBNETWORK_SIZE*0.99))

    def test_no_subnetwork_v3_empty(self):
        for nodes_factor in reversed(NODES_OVER_NETWORK_SIZE):
            total_nodes = int(SUBNETWORK_SIZE * nodes_factor)
            nodes = [uuid4() for _ in range(total_nodes)]
            replication_factor = ceil(3/nodes_factor)
            minimum_membership = calculate_minimum_membership(SUBNETWORK_SIZE, total_nodes, 1)
            subsets = set(
                chain.from_iterable(
                    generate_distribution_set_v3(
                        blake2b(_id.bytes).digest(),
                        minimum_membership,
                        replication_factor,
                        SUBNETWORK_SIZE
                    )
                    for _id in nodes
                )
            )
            print(f"Total nodes: {total_nodes}")
            self.assertGreater(len(subsets), floor(SUBNETWORK_SIZE*0.99))
