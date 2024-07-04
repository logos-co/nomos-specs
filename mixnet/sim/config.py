from __future__ import annotations

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
        config = dacite.from_dict(data_class=Config, data=data)

        # Validations
        config.simulation.validate()
        config.logic.validate()
        config.mixnet.validate()

        return config


@dataclass
class SimulationConfig:
    time_scale: float
    duration_sec: int
    net_latency_sec: float

    def validate(self):
        assert self.time_scale > 0
        assert self.duration_sec > 0
        assert self.net_latency_sec > 0

    def scale_time(self, time: float) -> float:
        return time * self.time_scale

    def scale_rate(self, rate: int) -> float:
        return float(rate / self.time_scale)

    def scaled_duration(self) -> float:
        return self.scale_time(self.duration_sec)

    def scaled_net_latency(self) -> float:
        return self.scale_time(self.net_latency_sec)


@dataclass
class LogicConfig:
    lottery_interval_sec: float
    sender_prob: float

    def validate(self):
        assert self.lottery_interval_sec > 0
        assert self.sender_prob > 0


@dataclass
class MixnetConfig:
    num_nodes: int
    transmission_rate_per_sec: int
    peering_degree: int
    max_mix_path_length: int

    def validate(self):
        assert self.num_nodes > 0
        assert self.transmission_rate_per_sec > 0
        assert self.peering_degree > 0
        assert self.max_mix_path_length > 0

    def node_configs(self) -> list[NodeConfig]:
        return [
            NodeConfig(
                X25519PrivateKey.generate(),
                self.peering_degree,
                self.transmission_rate_per_sec,
            )
            for _ in range(self.num_nodes)
        ]
