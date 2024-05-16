from dataclasses import dataclass
from typing import Self

import dacite
import yaml


@dataclass
class Config:
    running_time: int
    num_nodes: int
    num_mix_layers: int
    # An interval of sending a new real/cover message
    # A probability of actually sending a message depends on the following parameters.
    message_interval: int
    # A probability of sending a real message within one cycle
    real_message_prob: float
    # A weight of real message emission probability of some nodes
    # Each weight is assigned to each node in the order of the node ID.
    # The length of the list should be <= num_nodes. i.e. some nodes won't have a weight.
    real_message_prob_weights: list[float]
    # A probability of sending a cover message within one cycle if not sending a real message
    cover_message_prob: float
    # A maximum preparation time (delay) before sending the message
    max_message_prep_time: float
    # A maximum network latency between nodes directly connected with each other
    max_network_latency: float
    # A maximum delay of messages mixed in a mix node
    max_mix_delay: float
    # A discrete time window for the adversary to observe inputs and outputs of a certain node
    io_observation_window: int

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
        assert config.real_message_prob > 0
        assert len(config.real_message_prob_weights) <= config.num_nodes
        for weight in config.real_message_prob_weights:
            assert weight >= 1
        assert config.cover_message_prob >= 0
        assert config.max_message_prep_time >= 0
        assert config.max_network_latency >= 0
        assert config.io_observation_window >= 0

        return config
