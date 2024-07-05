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
    logic: LogicConfig
    mixnet: MixnetConfig

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
        config.logic.validate()
        config.mixnet.validate()

        return config


@dataclass
class SimulationConfig:
    duration_sec: int
    net_latency_sec: float

    def validate(self):
        assert self.duration_sec > 0
        assert self.net_latency_sec > 0


@dataclass
class LogicConfig:
    sender_lottery: LotteryConfig

    def validate(self):
        self.sender_lottery.validate()


@dataclass
class LotteryConfig:
    interval_sec: float
    probability: float
    seed: random.Random

    def validate(self):
        assert self.interval_sec > 0
        assert self.probability > 0
        assert self.seed is not None


@dataclass
class MixnetConfig:
    num_nodes: int
    transmission_rate_per_sec: int
    peering: PeeringConfig
    mix_path: MixPathConfig

    def validate(self):
        assert self.num_nodes > 0
        assert self.transmission_rate_per_sec > 0
        self.peering.validate()
        self.mix_path.validate()

    def node_configs(self) -> list[NodeConfig]:
        return [
            NodeConfig(
                self._gen_private_key(i),
                self.peering.degree,
                self.transmission_rate_per_sec,
            )
            for i in range(self.num_nodes)
        ]

    def _gen_private_key(self, node_idx: int) -> X25519PrivateKey:
        return X25519PrivateKey.from_private_bytes(
            hashlib.sha256(node_idx.to_bytes(4, "big")).digest()[:32]
        )


@dataclass
class PeeringConfig:
    degree: int

    def validate(self):
        assert self.degree > 0


@dataclass
class MixPathConfig:
    max_length: int
    seed: random.Random

    def validate(self):
        assert self.max_length > 0
        assert self.seed is not None


def seed_to_random(seed: int) -> random.Random:
    return random.Random(seed)
