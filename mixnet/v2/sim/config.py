from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Self

import dacite
import yaml

from environment import Time


@dataclass
class Config:
    simulation: SimulationConfig
    mixnet: MixnetConfig
    p2p: P2PConfig
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

    def description(self):
        return (
            f"{self.mixnet.description()}\n"
            f"{self.p2p.description()}"
        )


@dataclass
class SimulationConfig:
    running_time: Time

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
    message_interval: Time
    # A probability of sending a real message within one cycle
    real_message_prob: float
    # A weight of real message emission probability of some nodes
    # Each weight is multiplied to the real_message_prob of the node being at the same position in the node list.
    # The length of the list should be <= num_nodes. i.e. some nodes won't have a weight.
    real_message_prob_weights: list[float]
    # A probability of sending a cover message within one cycle if not sending a real message
    cover_message_prob: float
    # A maximum preparation time (computation time) for a message sender before sending the message
    max_message_prep_time: Time
    # A maximum delay of messages mixed in a mix node
    min_mix_delay: Time
    max_mix_delay: Time

    def validate(self):
        assert self.num_nodes > 0
        assert 0 <= self.num_mix_layers <= self.num_nodes
        assert self.payload_size > 0
        assert self.message_interval > 0
        assert self.real_message_prob > 0
        assert len(self.real_message_prob_weights) <= self.num_nodes
        for weight in self.real_message_prob_weights:
            assert weight >= 1
        assert self.cover_message_prob >= 0
        assert self.max_message_prep_time >= 0
        assert 0 <= self.min_mix_delay <= self.max_mix_delay

    def description(self):
        return (
            f"payload: {self.payload_size} bytes\n"
            f"num_nodes: {self.num_nodes}\n"
            f"num_mix_layers: {self.num_mix_layers}\n"
            f"min_mix_delay: {self.min_mix_delay}\n"
            f"max_mix_delay: {self.max_mix_delay}\n"
            f"msg_interval: {self.message_interval}\n"
            f"real_msg_prob: {self.real_message_prob:.2f}\n"
            f"cover_msg_prob: {self.cover_message_prob:.2f}"
        )

    def is_mixing_on(self) -> bool:
        return self.num_mix_layers > 0

    def random_mix_delay(self) -> Time:
        return random.randint(self.min_mix_delay, self.max_mix_delay)


@dataclass
class P2PConfig:
    # Broadcasting type: 1-to-all | gossip
    type: str
    # A connection density, only if the type is gossip
    connection_density: int
    # A maximum network latency between nodes directly connected with each other
    min_network_latency: Time
    max_network_latency: Time

    TYPE_ONE_TO_ALL = "1-to-all"
    TYPE_GOSSIP = "gossip"

    def validate(self):
        assert self.type in [self.TYPE_ONE_TO_ALL, self.TYPE_GOSSIP]
        if self.type == self.TYPE_GOSSIP:
            assert self.connection_density > 0
        assert 0 < self.min_network_latency <= self.max_network_latency

    def description(self):
        return (
            f"p2p_type: {self.type}\n"
            f"conn_density: {self.connection_density}\n"
            f"min_net_latency: {self.min_network_latency:.2f}\n"
            f"max_net_latency: {self.max_network_latency:.2f}"
        )

    def random_network_latency(self) -> Time:
        return random.randint(self.min_network_latency, self.max_network_latency)


@dataclass
class MeasurementConfig:
    # How many times in simulation represent 1 second in real time
    sim_time_per_second: Time

    def validate(self):
        assert self.sim_time_per_second > 0


@dataclass
class AdversaryConfig:
    timing_attack_max_targets: int
    timing_attack_max_pool_size: int

    def validate(self):
        assert self.timing_attack_max_targets > 0
        assert self.timing_attack_max_pool_size > 0
