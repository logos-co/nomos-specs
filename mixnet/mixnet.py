from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List

from mixnet.node import MixNode


class Mixnet:
    __topology: MixnetTopology | None = None

    def get_topology(self) -> MixnetTopology:
        if self.__topology is None:
            raise RuntimeError("topology is not set yet")
        return self.__topology

    def set_topology(self, topology: MixnetTopology) -> None:
        """
        Replace the old topology with the new topology received, and start establishing new network connections in background.

        In real implementations, this method should be a long-running task, accepting topologies periodically.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__topology = topology
        self.__establish_connections()

    def __establish_connections(self) -> None:
        """
        Establish network connections in advance based on the topology received.

        This is just a preparation to forward subsequent packets as quickly as possible,
        but this is not a strict requirement.

        In real implementations, this should be a background task.
        """
        pass


@dataclass
class MixnetTopology:
    # In production, this can be a 1-D array, which is accessible by indexes.
    # Here, we use a 2-D array for readability.
    layers: List[List[MixNode]]

    def generate_route(self) -> list[MixNode]:
        return [random.choice(layer) for layer in self.layers]

    def choose_mix_destionation(self) -> MixNode:
        all_mixnodes = [mixnode for layer in self.layers for mixnode in layer]
        return random.choice(all_mixnodes)


@dataclass
class MixnetTopologySize:
    num_layers: int
    num_mixnodes_per_layer: int

    def num_total_mixnodes(self) -> int:
        return self.num_layers * self.num_mixnodes_per_layer
