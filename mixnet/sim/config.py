from __future__ import annotations

from dataclasses import dataclass

import dacite
import yaml
from pysphinx.sphinx import X25519PrivateKey

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
    duration_sec: int

    def validate(self):
        assert self.duration_sec > 0

    def description(self):
        return f"running_secs: {self.duration_sec}"


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
