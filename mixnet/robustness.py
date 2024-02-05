from __future__ import annotations

from dataclasses import dataclass
from typing import List

from mixnet.config import MixnetConfig, MixnetTopology, MixNodeInfo
from mixnet.fisheryates import FisherYates
from mixnet.mixnet import Mixnet


class Robustness:
    """
    A robustness layer is placed on top of a mixnet layer and a consensus layer,
    to separate their responsibilities and minimize dependencies between them.

    For v1, the role of robustness layer is building a new mixnet topology
    and injecting it to the mixnet layer,
    whenever a new entropy is received from the consensus layer.
    A static list of nodes is used for building topologies deterministically.
    This can be changed in later versions.

    In later versions, the robustness layer will have more responsibilities.
    """

    def __init__(
        self,
        config: RobustnessConfig,
        mixnet: Mixnet,
    ) -> None:
        self.__config = config
        self.__mixnet = mixnet

    def set_entropy(self, entropy: bytes) -> None:
        """
        Given a entropy received, build a new topology and send it to mixnet.
        In v1, this doesn't change any mixnet config except topology.

        In real implementations, this method should be a long-running task, consuming entropy periodically.
        Here in the spec, this method has been simplified as a setter, assuming the single-thread test environment.
        """
        self.__config.mixnet.mixnet_layer_config.topology = self.build_topology(
            self.__config.mixnet.mixnode_candidates,
            self.__config.mixnet.topology_size,
            entropy,
        )
        self.__mixnet.set_config(self.__config.mixnet.mixnet_layer_config)

    @staticmethod
    def build_topology(
        mixnode_candidates: List[MixNodeInfo],
        mixnet_topology_size: MixnetTopologySize,
        entropy: bytes,
    ) -> MixnetTopology:
        """
        Build a new topology deterministically using an entropy and a given set of candidates.
        """
        shuffled = FisherYates.shuffle(mixnode_candidates, entropy)
        sampled = shuffled[: mixnet_topology_size.num_total_mixnodes()]

        layers = []
        for layer_id in range(mixnet_topology_size.num_layers):
            start = layer_id * mixnet_topology_size.num_mixnodes_per_layer
            layer = sampled[start : start + mixnet_topology_size.num_mixnodes_per_layer]
            layers.append(layer)
        return MixnetTopology(layers)


@dataclass
class RobustnessConfig:
    """In v1, the robustness layer manages configs only for the mixnet layer."""

    mixnet: RobustnessMixnetConfig


class RobustnessMixnetConfig:
    """
    Configurations for the mixnet layer
    These configurations are meant to be changed over time according to other parameters from other layers (e.g. consensus).
    """

    def __init__(
        self,
        mixnode_candidates: List[MixNodeInfo],
        mixnet_topology_size: MixnetTopologySize,
        mixnet_layer_config: MixnetConfig,
    ) -> None:
        assert mixnet_topology_size.num_total_mixnodes() <= len(mixnode_candidates)
        self.mixnode_candidates = mixnode_candidates
        self.topology_size = mixnet_topology_size
        # A config to be injected to the mixnet layer whenever it is updated
        self.mixnet_layer_config = mixnet_layer_config


@dataclass
class MixnetTopologySize:
    num_layers: int
    num_mixnodes_per_layer: int

    def num_total_mixnodes(self) -> int:
        return self.num_layers * self.num_mixnodes_per_layer
