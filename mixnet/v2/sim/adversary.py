from __future__ import annotations

import math
from collections import defaultdict, deque
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
        self.msgs_in_node_per_window = []  # [<receiver, (int, set[sender]))>]
        self.cur_window_per_node = defaultdict(lambda: deque())  # <node, [(time, int)]>: int is + or -.
        # self.node_states = defaultdict(dict)

        self.env.process(self.update_observation_window())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_receiving_node(self, sender: "Node", receiver: "Node"):
        self.cur_window_per_node[receiver].append((self.env.now, 1, sender))
        # if node not in self.node_states[self.env.now]:
        #     self.node_states[self.env.now][node] = NodeState.RECEIVING

    def observe_sending_node(self, sender: "Node", receiver: "Node"):
        self.cur_window_per_node[sender].append((self.env.now, -1, receiver))
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval[sender] += 1
        # self.node_states[self.env.now][node] = NodeState.SENDING

    def is_around_message_interval(self, time: SimTime):
        now_frac, now_int = math.modf(time)
        return now_int % self.config.mixnet.message_interval == 0 and now_frac <= self.config.mixnet.max_message_prep_time

    def update_observation_window(self):
        while True:
            yield self.env.timeout(self.config.adversary.io_window_moving_interval)

            self.msgs_in_node_per_window.append(defaultdict(lambda: (0, set())))  # <node, (int, int)>
            for node, queue in self.cur_window_per_node.items():
                msg_cnt = 0.0
                senders = set()
                # Pop old events that are out of the new window, and accumulate msg_cnt
                while queue and queue[0][0] < self.env.now - self.config.adversary.io_window_size:
                    _, delta, sender = queue.popleft()
                    msg_cnt += delta
                    senders.add(sender)
                # Iterate remaining events that will remain in the new window, and accumulate msg_cnt
                for _, delta, sender in queue:
                    msg_cnt += delta
                    senders.add(sender)
                self.msgs_in_node_per_window[-1][node] = (msg_cnt, senders)


class NodeState(Enum):
    SENDING = 0
    RECEIVING = 1
