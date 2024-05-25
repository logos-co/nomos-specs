from __future__ import annotations

import math
from collections import defaultdict
from enum import Enum
from typing import TYPE_CHECKING

import simpy
from simpy.core import SimTime

from config import Config
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node


class Adversary:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.message_sizes = []
        self.senders_around_interval = defaultdict(int)
        self.mixed_msgs_per_window = []
        # self.node_states = defaultdict(dict)

        self.env.process(self.update_observation_window())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_receiving_node(self, node: "Node"):
        self.mixed_msgs_per_window[-1][node] += 1
        # if node not in self.node_states[self.env.now]:
        #     self.node_states[self.env.now][node] = NodeState.RECEIVING

    def observe_sending_node(self, node: "Node"):
        self.mixed_msgs_per_window[-1][node] -= 1
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval[node] += 1
        # self.node_states[self.env.now][node] = NodeState.SENDING

    def is_around_message_interval(self, time: SimTime):
        now_frac, now_int = math.modf(time)
        return now_int % self.config.mixnet.message_interval == 0 and now_frac <= self.config.mixnet.max_message_prep_time

    def update_observation_window(self):
        while True:
            self.mixed_msgs_per_window.append(defaultdict(int))
            yield self.env.timeout(self.config.adversary.io_observation_window)


class NodeState(Enum):
    SENDING = 0
    RECEIVING = 1
