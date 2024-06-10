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
        self.io_windows = []  # dict[receiver, (deque[time_received], set[sender]))]
        self.io_windows.append(defaultdict(lambda: (deque(), set())))
        self.final_msgs_received = defaultdict(dict)  # dict[receiver, dict[window, sender]]
        # self.node_states = defaultdict(dict)

        self.env.process(self.update_observation_window())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_receiving_node(self, sender: "Node", receiver: "Node", msg: SphinxPacket | bytes):
        msg_queue, senders = self.io_windows[-1][receiver]
        msg_queue.append(self.env.now)
        senders.add(sender)
        if receiver.operated_by_adversary and not isinstance(msg, SphinxPacket):
            self.final_msgs_received[receiver][len(self.io_windows) - 1] = sender
        # if node not in self.node_states[self.env.now]:
        #     self.node_states[self.env.now][node] = NodeState.RECEIVING

    def observe_sending_node(self, sender: "Node"):
        msg_queue, _ = self.io_windows[-1][sender]
        if len(msg_queue) > 0:
            # Adversary doesn't know which message in the pool is being emitted. So, pop the oldest one from the pool.
            msg_queue.popleft()
        if self.is_around_message_interval(self.env.now):
            self.senders_around_interval.update({sender})
        # self.node_states[self.env.now][node] = NodeState.SENDING

    def is_around_message_interval(self, time: SimTime):
        return time % self.config.mixnet.message_interval <= self.config.mixnet.max_message_prep_time

    def update_observation_window(self):
        while True:
            yield self.env.timeout(self.config.adversary.io_window_size)
            new_window = defaultdict(lambda: (deque(), set()))
            for receiver, (msg_queue, _) in self.io_windows[-1].items():
                for time_received in msg_queue:
                    # If the message is likely to be still pending and be emitted soon, pass it on to the next window.
                    if self.env.now - time_received < self.config.mixnet.max_mix_delay:
                        new_window[receiver][0].append(time_received)
            self.io_windows.append(new_window)


class NodeState(Enum):
    SENDING = 0
    RECEIVING = 1
