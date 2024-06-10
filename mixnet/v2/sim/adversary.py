from __future__ import annotations

from collections import defaultdict, deque, Counter
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
        self.senders_around_interval = Counter()
        self.msg_pools_per_window = []  # list[dict[receiver, deque[time_received])]]
        self.msg_pools_per_window.append(defaultdict(lambda: deque()))
        self.msgs_received_per_window = []  # list[dict[receiver, set[sender])]]
        self.msgs_received_per_window.append(defaultdict(set))
        # dict[receiver, dict[window, list[(sender, origin_id)]]]
        self.final_msgs_received = defaultdict(lambda: defaultdict(list))
        # self.node_states = defaultdict(dict)

        self.env.process(self.update_observation_window())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_receiving_node(self, sender: "Node", receiver: "Node", msg: SphinxPacket | bytes):
        cur_window = len(self.msg_pools_per_window) - 1
        self.msg_pools_per_window[cur_window][receiver].append(self.env.now)
        self.msgs_received_per_window[cur_window][receiver].add(sender)

        origin_id = receiver.inspect_message(msg)
        if origin_id is not None:
            self.final_msgs_received[receiver][cur_window].append((sender, origin_id))
        # if node not in self.node_states[self.env.now]:
        #     self.node_states[self.env.now][node] = NodeState.RECEIVING

    def observe_sending_node(self, sender: "Node"):
        msg_pool = self.msg_pools_per_window[-1][sender]
        if len(msg_pool) > 0:
            # Adversary doesn't know which message in the pool is being emitted. So, pop the oldest one from the pool.
            msg_pool.popleft()
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval.update({sender})
        # self.node_states[self.env.now][node] = NodeState.SENDING

    def is_around_message_interval(self, time: SimTime):
        return time % self.config.mixnet.message_interval <= self.config.mixnet.max_message_prep_time

    def update_observation_window(self):
        while True:
            yield self.env.timeout(self.config.adversary.window_size)

            self.msgs_received_per_window.append(defaultdict(set))

            new_msg_pool = defaultdict(lambda: deque())
            for receiver, msg_queue in self.msg_pools_per_window[-1].items():
                for time_received in msg_queue:
                    # If the message is likely to be still pending and be emitted soon, pass it on to the next window.
                    if self.env.now - time_received < self.config.mixnet.max_mix_delay:
                        new_msg_pool[receiver][0].append(time_received)
            self.msg_pools_per_window.append(new_msg_pool)


class NodeState(Enum):
    SENDING = 0
    RECEIVING = 1
