from __future__ import annotations
from dataclasses import dataclass
from typing import Self

import dacite
import yaml


@dataclass
class Config:
    simulation: SimulationConfig
    mixnet: MixnetConfig
    p2p: P2pConfig
    measurement: MeasurementConfig
    adversary: AdversaryConfig

    @classmethod
    def load(cls, yaml_path: str) -> Self:
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        config = dacite.from_dict(data_class=Config, data=data)

        # Validations
        config.simulation.validate()
        config.mixnet.validate()
        config.p2p.validate()
        config.measurement.validate()
        config.adversary.validate()
        
        return config


@dataclass
class SimulationConfig:
    running_time: int

    def validate(self):
        assert self.running_time > 0


@dataclass
class MixnetConfig:
    num_nodes: int
    num_mix_layers: int
    # A size of a message payload in bytes (e.g. the size of a block proposal)
    payload_size: int
    # An interval of sending a new real/cover message
    # A probability of actually sending a message depends on the following parameters.
    message_interval: int
    # A probability of sending a real message within one cycle
    real_message_prob: float
    # A weight of real message emission probability of some nodes
    # Each weight is multiplied to the real_message_prob of the node being at the same position in the node list.
    # The length of the list should be <= num_nodes. i.e. some nodes won't have a weight.
    real_message_prob_weights: list[float]
    # A probability of sending a cover message within one cycle if not sending a real message
    cover_message_prob: float
    # A maximum preparation time (delay) before sending the message
    max_message_prep_time: float
    # A maximum delay of messages mixed in a mix node
    max_mix_delay: float

    def validate(self):
        assert self.num_nodes > 0
        assert 0 < self.num_mix_layers <= self.num_nodes
        assert self.payload_size > 0
        assert self.message_interval > 0
        assert self.real_message_prob > 0
        assert len(self.real_message_prob_weights) <= self.num_nodes
        for weight in self.real_message_prob_weights:
            assert weight >= 1
        assert self.cover_message_prob >= 0
        assert self.max_message_prep_time >= 0
        assert self.max_mix_delay >= 0


@dataclass
class P2pConfig:
    # A maximum network latency between nodes directly connected with each other
    max_network_latency: float

    def validate(self):
        assert self.max_network_latency >= 0


@dataclass
class MeasurementConfig:
    # How many times in simulation represent 1 second in real time
    sim_time_per_second: float

    def validate(self):
        assert self.sim_time_per_second > 0


@dataclass
class AdversaryConfig:
    # A discrete time window for the adversary to observe inputs and outputs of a certain node
    io_observation_window: int

    def validate(self):
        assert self.io_observation_window >= 1
