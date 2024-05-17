import math
from collections import defaultdict
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
        self.env.process(self.update_observation_window())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_incoming_message(self, node: "Node"):
        self.mixed_msgs_per_window[-1][node] += 1

    def observe_outgoing_message(self, node: "Node"):
        self.mixed_msgs_per_window[-1][node] -= 1
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval[node] += 1

    def is_around_message_interval(self, time: SimTime):
        now_frac, now_int = math.modf(time)
        return now_int % self.config.message_interval == 0 and now_frac <= self.config.max_message_prep_time

    def update_observation_window(self):
        while True:
            self.mixed_msgs_per_window.append(defaultdict(int))
            yield self.env.timeout(self.config.io_observation_window)
