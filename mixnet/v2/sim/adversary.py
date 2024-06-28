from __future__ import annotations

from collections import defaultdict, deque, Counter
from enum import Enum
from typing import TYPE_CHECKING

from config import Config
from environment import Environment, Time
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node


class Adversary:
    def __init__(self, env: Environment, config: Config):
        self.env = env
        self.config = config
        self.message_sizes = []
        self.senders_around_interval = Counter()
        self.msg_pools_per_time = []  # list[dict[receiver, deque[time_received])]]
        self.msg_pools_per_time.append(defaultdict(lambda: deque()))
        self.msgs_received_per_time = []  # list[dict[receiver, dict[sender, list[time_sent]]]]
        self.msgs_received_per_time.append(defaultdict(lambda: defaultdict(list)))
        # dict[receiver, dict[time, list[(sender, time_sent, origin_id)]]]
        self.final_msgs_received = defaultdict(lambda: defaultdict(list))
        # self.node_states = defaultdict(dict)

        self.env.process(self.update_observation_time())

    def inspect_message_size(self, msg: SphinxPacket | bytes):
        self.message_sizes.append(len(msg))

    def observe_receiving_node(self, sender: "Node", receiver: "Node", time_sent: Time):
        self.msg_pools_per_time[-1][receiver].append(self.env.now())
        self.msgs_received_per_time[-1][receiver][sender].append(time_sent)
        # if node not in self.node_states[self.env.now]:
        #     self.node_states[self.env.now][node] = NodeState.RECEIVING

    def observe_sending_node(self, sender: "Node"):
        msg_pool = self.msg_pools_per_time[-1][sender]
        if len(msg_pool) > 0:
            # Adversary doesn't know which message in the pool is being emitted. So, pop the oldest one from the pool.
            msg_pool.popleft()
        if self.is_around_message_interval(self.env.now()):
            self.senders_around_interval.update({sender})
        # self.node_states[self.env.now][node] = NodeState.SENDING

    def observe_if_final_msg(self, sender: "Node", receiver: "Node", time_sent: Time, msg: SphinxPacket | bytes):
        origin_id = receiver.inspect_message(msg)
        if origin_id is not None:
            cur_time = len(self.msgs_received_per_time) - 1
            self.final_msgs_received[receiver][cur_time].append((sender, time_sent, origin_id))

    def is_around_message_interval(self, time: Time) -> bool:
        return time % self.config.mixnet.message_interval <= self.config.mixnet.max_message_prep_time

    def update_observation_time(self):
        while True:
            yield self.env.timeout(1)

            self.msgs_received_per_time.append(defaultdict(lambda: defaultdict(list)))

            new_msg_pool = defaultdict(lambda: deque())
            for receiver, msg_queue in self.msg_pools_per_time[-1].items():
                for time_received in msg_queue:
                    # If the message is likely to be still pending and be emitted soon,
                    # pass it on to the next time slot.
                    if self.env.now() - time_received < self.config.mixnet.max_mix_delay:
                        new_msg_pool[receiver][0].append(time_received)
            self.msg_pools_per_time.append(new_msg_pool)


class NodeState(Enum):
    SENDING = 0
    RECEIVING = 1
