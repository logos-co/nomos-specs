from dataclasses import dataclass


@dataclass
class Config:
    running_time: int
    num_nodes: int
    num_mix_layers: int
    message_interval: int
    message_prob: float
    max_message_prep_time: float
