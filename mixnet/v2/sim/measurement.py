from collections import defaultdict, Counter
from typing import TYPE_CHECKING

import pandas as pd
import simpy

from config import Config
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node


class Measurement:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.original_senders = Counter()
        self.egress_bandwidth_per_time = []
        self.ingress_bandwidth_per_time = []
        self.message_hops = defaultdict(int)  # dict[msg_hash, hops]

        self.env.process(self._update_bandwidth_window())

    def set_nodes(self, nodes: list["Node"]):
        for node in nodes:
            self.original_senders[node] = 0

    def count_original_sender(self, sender: "Node"):
        self.original_senders.update({sender})

    def measure_egress(self, node: "Node", msg: SphinxPacket | bytes):
        self.egress_bandwidth_per_time[-1][node] += len(msg)

    def measure_ingress(self, node: "Node", msg: SphinxPacket | bytes):
        self.ingress_bandwidth_per_time[-1][node] += len(msg)

    def update_message_hops(self, msg_hash: bytes, hops: int):
        self.message_hops[msg_hash] = max(hops, self.message_hops[msg_hash])

    def _update_bandwidth_window(self):
        while True:
            self.ingress_bandwidth_per_time.append(defaultdict(int))
            self.egress_bandwidth_per_time.append(defaultdict(int))
            yield self.env.timeout(self.config.measurement.sim_time_per_second)

    def bandwidth(self) -> (pd.Series, pd.Series):
        nonzero_egresses, nonzero_ingresses = [], []
        for egress_bandwidths, ingress_bandwidths in zip(self.egress_bandwidth_per_time,
                                                         self.ingress_bandwidth_per_time):
            for bandwidth in egress_bandwidths.values():
                if bandwidth > 0:
                    nonzero_egresses.append(bandwidth / 1024.0)
            for bandwidth in ingress_bandwidths.values():
                if bandwidth > 0:
                    nonzero_ingresses.append(bandwidth / 1024.0)
        return pd.Series(nonzero_egresses), pd.Series(nonzero_ingresses)
