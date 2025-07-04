import random
from itertools import chain
from typing import List, Counter
from unittest import TestCase
from da.assignations.refill import calculate_subnetwork_assignations, Assignations, DeclarationId


class TestRefill(TestCase):
    def test_single_with(self, subnetworks_size = 2048, replication_factor: int = 3, network_size: int = 100):
        random_seed = random.randbytes(32)
        nodes = [random.randbytes(32) for _ in range(network_size)]
        previous_nodes = [set() for _ in range(subnetworks_size)]
        assignations = calculate_subnetwork_assignations(nodes, previous_nodes, replication_factor, random_seed)
        self.assert_assignations(assignations, nodes, replication_factor)

    def test_single_network_sizes(self):
        for i in [500, 1000, 10000, 100000]:
            with self.subTest(i):
                self.test_single_with(network_size=i)

    def test_evolving_increasing_network(self):
        random_seed = random.randbytes(32)
        network_size = 100
        replication_factor = 3
        nodes = [random.randbytes(32) for _ in range(network_size)]
        assignations = [set() for _ in range(2048)]
        assignations = calculate_subnetwork_assignations(nodes, assignations, replication_factor, random_seed)
        new_nodes = nodes
        for network_size in [300, 500, 1000, 10000, 100000]:
            random_seed = random.randbytes(32)
            new_nodes = self.expand_nodes(new_nodes, network_size - len(nodes))
            self.mutate_nodes(new_nodes, network_size//3)
            assignations = calculate_subnetwork_assignations(new_nodes, assignations, replication_factor, random_seed)
            self.assert_assignations(assignations, new_nodes, replication_factor)

    def test_evolving_decreasing_network(self):
        random_seed = random.randbytes(32)
        network_size = 100000
        replication_factor = 3
        nodes = [random.randbytes(32) for _ in range(network_size)]
        assignations = [set() for _ in range(2048)]
        assignations = calculate_subnetwork_assignations(nodes, assignations, replication_factor, random_seed)
        new_nodes = nodes
        for network_size in reversed([100, 300, 500, 1000, 10000]):
            random_seed = random.randbytes(32)
            new_nodes = self.shrink_nodes(new_nodes, network_size)
            self.mutate_nodes(new_nodes, network_size//3)
            assignations = calculate_subnetwork_assignations(new_nodes, assignations, replication_factor, random_seed)
            self.assert_assignations(assignations, new_nodes, replication_factor)


    def test_random_increase_decrease_network(self):
        random_seed = random.randbytes(32)
        network_size = 10000
        replication_factor = 3
        nodes = [random.randbytes(32) for _ in range(network_size)]
        assignations = [set() for _ in range(2048)]
        assignations = calculate_subnetwork_assignations(nodes, assignations, replication_factor, random_seed)
        new_nodes = nodes
        for step in (random.randrange(100, 1000) for _ in range(100)):
            random_seed = random.randbytes(32)
            if bool(random.choice((0, 1))):
                network_size += step
                new_nodes = self.expand_nodes(new_nodes, network_size)
            else:
                network_size -= step
                new_nodes = self.shrink_nodes(new_nodes, network_size)
            self.mutate_nodes(new_nodes, network_size//3)
            assignations = calculate_subnetwork_assignations(new_nodes, assignations, replication_factor, random_seed)
            self.assert_assignations(assignations, new_nodes, replication_factor)


    @classmethod
    def mutate_nodes(cls, nodes: List[DeclarationId], count: int):
        assert count < len(nodes)
        for i in random.choices(list(range(len(nodes))), k=count):
            nodes[i] = random.randbytes(32)

    @classmethod
    def expand_nodes(cls, nodes: List[DeclarationId], count: int) -> List[DeclarationId]:
        return [*nodes, *(random.randbytes(32) for _ in range(count))]

    @classmethod
    def shrink_nodes(cls, nodes: List[DeclarationId], count: int) -> List[DeclarationId]:
        return list(random.sample(nodes, k=count))


    def assert_assignations(self, assignations: Assignations, nodes: List[DeclarationId], replication_factor: int):
        self.assertEqual(
            len(set(chain.from_iterable(assignations))),
            len(nodes),
            "Only active nodes should be assigned"
        )
        self.assertTrue(
            all(len(assignation) >= replication_factor for assignation in assignations),
            f"No subnetworks should have less than {replication_factor} nodes"
        )
        self.assertAlmostEqual(
            max(map(len, assignations)),
            min(map(len, assignations)),
            msg="Subnetwork size variant should not be bigger than 1",
            delta=1
        )
        self.assertAlmostEqual(
            len(set(Counter(chain.from_iterable(assignations)).values())),
            1,
            msg="Nodes should be assigned uniformly to subnetworks",
            delta=1,
        )

