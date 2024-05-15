from dataclasses import dataclass
from typing import Self

import dacite
import yaml


@dataclass
class Config:
    running_time: int
    num_nodes: int
    num_mix_layers: int
    message_interval: int
    real_message_prob: float
    cover_message_prob: float
    max_message_prep_time: float

    @classmethod
    def load(cls, yaml_path: str) -> Self:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        config = dacite.from_dict(data_class=Config, data=data)

        # Validations
        assert config.running_time > 0
        assert config.num_nodes > 0
        assert 0 < config.num_mix_layers <= config.num_nodes
        assert config.message_interval > 0
        assert config.real_message_prob >= 0
        assert config.cover_message_prob >= 0
        assert config.real_message_prob + config.cover_message_prob <= 1
        assert config.max_message_prep_time >= 0

        return config
