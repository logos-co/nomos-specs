from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

import dacite
import yaml
from pysphinx.sphinx import X25519PrivateKey

from mixnet.config import NodeConfig


@dataclass
class Config:
    simulation: SimulationConfig
    network: NetworkConfig
    logic: LogicConfig
    mix: MixConfig

    @classmethod
    def load(cls, yaml_path: str) -> Config:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        config = dacite.from_dict(
            data_class=Config,
            data=data,
            config=dacite.Config(type_hooks={random.Random: seed_to_random}),
        )

        # Validations
        config.simulation.validate()
        config.network.validate()
        config.logic.validate()
        config.mix.validate()

        return config

    def node_configs(self) -> list[NodeConfig]:
        return [
            NodeConfig(
                self._gen_private_key(i),
                self.network.peering.degree,
                self.mix.transmission_rate_per_sec,
            )
            for i in range(self.network.num_nodes)
        ]

    def _gen_private_key(self, node_idx: int) -> X25519PrivateKey:
        return X25519PrivateKey.from_private_bytes(
            hashlib.sha256(node_idx.to_bytes(4, "big")).digest()[:32]
        )


@dataclass
class SimulationConfig:
    # Desired duration of the simulation in seconds
    # Since the simulation uses discrete time steps, the actual duration may be longer or shorter.
    duration_sec: int

    def validate(self):
        assert self.duration_sec > 0


@dataclass
class NetworkConfig:
    # Total number of nodes in the entire network.
    num_nodes: int
    latency: LatencyConfig
    peering: PeeringConfig

    def validate(self):
        assert self.num_nodes > 0
        self.latency.validate()
        self.peering.validate()


@dataclass
class LatencyConfig:
    # Maximum network latency between nodes in seconds.
    # A constant latency will be chosen randomly for each connection within the range [0, max_latency_sec].
    max_latency_sec: float
    # Seed for the random number generator used to determine the network latencies.
    seed: random.Random

    def validate(self):
        assert self.max_latency_sec > 0
        assert self.seed is not None

    def random_latency(self) -> float:
        # round to milliseconds to make analysis not too heavy
        return int(self.seed.random() * self.max_latency_sec * 1000) / 1000


@dataclass
class PeeringConfig:
    # Target number of peers each node can connect to (both inbound and outbound).
    degree: int

    def validate(self):
        assert self.degree > 0


@dataclass
class MixConfig:
    # Global constant transmission rate of each connection in messages per second.
    transmission_rate_per_sec: int
    mix_path: MixPathConfig

    def validate(self):
        assert self.transmission_rate_per_sec > 0
        self.mix_path.validate()


@dataclass
class MixPathConfig:
    # Maximum number of mix nodes to be chosen for a Sphinx packet.
    max_length: int
    # Seed for the random number generator used to determine the mix path.
    seed: random.Random

    def validate(self):
        assert self.max_length > 0
        assert self.seed is not None


def seed_to_random(seed: int) -> random.Random:
    return random.Random(seed)


@dataclass
class LogicConfig:
    sender_lottery: LotteryConfig

    def validate(self):
        self.sender_lottery.validate()


@dataclass
class LotteryConfig:
    # Interval between lottery draws in seconds.
    interval_sec: float
    # Probability of a node being selected as a sender in each lottery draw.
    probability: float
    # Seed for the random number generator used to determine the lottery winners.
    seed: random.Random

    def validate(self):
        assert self.interval_sec > 0
        assert self.probability >= 0
        assert self.seed is not None
