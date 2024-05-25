from collections import defaultdict
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
        self.egress_bandwidth_per_time = []
        self.ingress_bandwidth_per_time = []

        self.env.process(self._update_bandwidth_window())

    def measure_egress(self, node: "Node", msg: SphinxPacket | bytes):
        self.egress_bandwidth_per_time[-1][node] += len(msg)

    def measure_ingress(self, node: "Node", msg: SphinxPacket | bytes):
        self.ingress_bandwidth_per_time[-1][node] += len(msg)

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
