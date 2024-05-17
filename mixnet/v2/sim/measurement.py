from collections import defaultdict
from typing import TYPE_CHECKING

import simpy

from config import Config
from sphinx import SphinxPacket

if TYPE_CHECKING:
    from node import Node

class Measurement:
    def __init__(self, env: simpy.Environment, config: Config):
        self.env = env
        self.config = config
        self.ingress_bandwidth_per_time = []
        self.egress_bandwidth_per_time = []

        self.env.process(self.update_bandwidth_window())

    def measure_ingress(self, node: "Node", msg: SphinxPacket | bytes):
        self.ingress_bandwidth_per_time[-1][node] += len(msg)

    def measure_egress(self, node: "Node", msg: SphinxPacket | bytes):
        self.egress_bandwidth_per_time[-1][node] += len(msg)

    def update_bandwidth_window(self):
        while True:
            self.ingress_bandwidth_per_time.append(defaultdict(int))
            self.egress_bandwidth_per_time.append(defaultdict(int))
            yield self.env.timeout(self.config.measurement.sim_time_per_second)

