from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Thread
from typing import List

from mixnet.fisheryates import FisherYates
from mixnet.node import MixNode


@dataclass
class Mixnet:
    mix_nodes: List[MixNode]

    def __init__(
        self,
        mix_nodes: List[MixNode],
        n_layers: int,
        n_nodes_per_layer: int,
        mixnet_epoch_sec: int,
        proactive_sec: int,
        initial_entropy: bytes,
    ):
        self.mix_nodes = mix_nodes

        self.set_entropy(initial_entropy)

        self.topology_updater = MixnetTopologyUpdater(
            mix_nodes, n_layers, n_nodes_per_layer, mixnet_epoch_sec, proactive_sec
        )
        self.topology_updater.daemon = True
        self.topology_updater.start()

    def set_entropy(self, entropy: bytes) -> None:
        """
        Set entropy (seed) to the Fisher-Yates shuffler
        that is going to be used for deterministic topology construction.

        This method is expected to be called periodically by the user.
        Until the next entropy is provides, Fisher-Yates shuffler continues to works
        based on this entropy set once.
        """
        FisherYates.set_seed(entropy)

    def choose_mixnode(self) -> MixNode:
        return random.choice(self.mix_nodes)

    def current_topology(self) -> MixnetTopology:
        return self.topology_updater.current_topology()


class MixnetTopologyUpdater(Thread):
    def __init__(
        self,
        mix_nodes: List[MixNode],
        n_layers: int,
        n_nodes_per_layer: int,
        mixnet_epoch_sec: int,
        proactive_sec: int,
    ):
        super().__init__()
        self.mix_nodes = mix_nodes
        self.n_layers = n_layers
        self.n_nodes_per_layer = n_nodes_per_layer
        self.mixnet_epoch_sec = mixnet_epoch_sec
        self.proactive_sec = proactive_sec

        self.lock = threading.Lock()
        self.topology = self.build_topology()
        self.next_topology = None

    def run(self) -> None:
        next_epoch_ts = datetime.now() + timedelta(seconds=self.mixnet_epoch_sec)

        while True:
            time.sleep(1 / 1000)

            now = datetime.now()
            if now < next_epoch_ts - timedelta(seconds=self.proactive_sec):
                continue

            if self.next_topology is None:
                self.next_topology = self.build_topology()

            if now < next_epoch_ts:
                continue

            with self.lock:
                self.topology = self.next_topology
                self.next_topology = None
            next_epoch_ts = now + timedelta(seconds=self.mixnet_epoch_sec)

    def current_topology(self):
        with self.lock:
            return self.topology

    def build_topology(
        self,
    ) -> MixnetTopology:
        num_nodes = self.n_nodes_per_layer * self.n_layers
        assert num_nodes <= len(self.mix_nodes)

        shuffled = FisherYates.shuffle(self.mix_nodes)
        sampled = shuffled[:num_nodes]
        layers = []
        for l in range(self.n_layers):
            start = l * self.n_nodes_per_layer
            layer = sampled[start : start + self.n_nodes_per_layer]
            layers.append(layer)

        # With this new topology, network connections with the adjacent mix layer should be established.
        # In this specification, we skip implementing connections for simplicity.
        return MixnetTopology(layers)


@dataclass
class MixnetTopology:
    layers: List[List[MixNode]]

    def generate_route(self) -> list[MixNode]:
        return [random.choice(layer) for layer in self.layers]
