from __future__ import annotations

from dataclasses import dataclass

import dacite
import yaml
from pysphinx.sphinx import X25519PrivateKey
from simpy.core import SimTime

from mixnet.config import NodeConfig


@dataclass
class Config:
    simulation: SimulationConfig
    mixnet: MixnetConfig

    @classmethod
    def load(cls, yaml_path: str) -> Config:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        config = dacite.from_dict(data_class=Config, data=data)

        # Validations
        config.simulation.validate()
        config.mixnet.validate()

        return config

    def description(self):
        return f"{self.simulation.description()}\n" f"{self.mixnet.description()}"


@dataclass
class SimulationConfig:
    running_time: SimTime

    def validate(self):
        # SimTime supports float but better to use int for time accuracy
        assert isinstance(self.running_time, int) and self.running_time > 0

    def description(self):
        return f"running_time: {self.running_time}"


@dataclass
class MixnetConfig:
    num_nodes: int
    transmission_rate_per_sec: int

    def validate(self):
        assert self.num_nodes > 0
        assert self.transmission_rate_per_sec > 0

    def description(self):
        return (
            f"num_nodes: {self.num_nodes}\n"
            f"transmission_rate_per_sec: {self.transmission_rate_per_sec}"
        )

    def node_configs(self) -> list[NodeConfig]:
        return [
            NodeConfig(X25519PrivateKey.generate(), self.transmission_rate_per_sec)
            for _ in range(self.num_nodes)
        ]
