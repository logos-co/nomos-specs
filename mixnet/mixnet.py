from __future__ import annotations

import random
import threading
import time
import queue
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Thread
from typing import List, TypeAlias

from mixnet.fisheryates import FisherYates
from mixnet.node import MixNode


EntropyQueue: TypeAlias = "queue.Queue[bytes]"


@dataclass
class Mixnet:
    mix_nodes: List[MixNode]

    def __init__(
        self,
        mix_nodes: List[MixNode],
        n_layers: int,
        n_nodes_per_layer: int,
        current_entropy: bytes,
        entropy_delay_sec: int,
    ):
        self.mix_nodes = mix_nodes

        self.entropy_queue: EntropyQueue = queue.Queue()
        self.topology_updater = MixnetTopologyUpdater(
            mix_nodes,
            n_layers,
            n_nodes_per_layer,
            current_entropy,
            entropy_delay_sec,
            self.entropy_queue,
        )
        self.topology_updater.daemon = True
        self.topology_updater.start()

    def choose_mixnode(self) -> MixNode:
        return random.choice(self.mix_nodes)

    def current_topology(self) -> MixnetTopology:
        return self.topology_updater.current_topology()

    def inject_entropy(self, entropy: bytes) -> None:
        self.entropy_queue.put(entropy)


class MixnetTopologyUpdater(Thread):
    def __init__(
        self,
        mix_nodes: List[MixNode],
        n_layers: int,
        n_nodes_per_layer: int,
        current_entropy: bytes,
        entropy_delay_sec: int,
        entropy_queue: EntropyQueue,
    ):
        super().__init__()
        self.mix_nodes = mix_nodes
        self.n_layers = n_layers
        self.n_nodes_per_layer = n_nodes_per_layer
        self.entropy_delay_sec = entropy_delay_sec
        self.entropy_queue = entropy_queue

        self.lock = threading.Lock()
        self.topology = self.build_topology(current_entropy)
        self.establish_conections(self.topology)

    def run(self) -> None:
        while True:
            new_entropy = self.entropy_queue.get(block=True)
            ts = datetime.now() + timedelta(seconds=self.entropy_delay_sec)

            next_topology = self.build_topology(new_entropy)
            self.establish_conections(next_topology)

            time.sleep((ts - datetime.now()).total_seconds())
            with self.lock:
                self.topology = next_topology

    def current_topology(self):
        with self.lock:
            return self.topology

    def build_topology(self, entropy: bytes) -> MixnetTopology:
        num_nodes = self.n_nodes_per_layer * self.n_layers
        assert num_nodes <= len(self.mix_nodes)

        shuffled = FisherYates.shuffle(self.mix_nodes, entropy)
        sampled = shuffled[:num_nodes]
        layers = []
        for l in range(self.n_layers):
            start = l * self.n_nodes_per_layer
            layer = sampled[start : start + self.n_nodes_per_layer]
            layers.append(layer)

        return MixnetTopology(layers)

    def establish_conections(self, _: MixnetTopology) -> None:
        """
        Establish connections with mix nodes in the adjacent mix layer.

        In this spec, the actual implementation is skipped for simplicity.
        """
        pass


@dataclass
class MixnetTopology:
    layers: List[List[MixNode]]

    def generate_route(self) -> list[MixNode]:
        return [random.choice(layer) for layer in self.layers]
