from typing import Optional, Any

import simpy

Time = int


class Environment:
    def __init__(self):
        self.env = simpy.Environment()

    def now(self) -> Time:
        return Time(self.env.now)

    def run(self, until: Time) -> Optional[Any]:
        return self.env.run(until=until)

    def timeout(self, timeout: Time) -> simpy.Timeout:
        return self.env.timeout(timeout)

    def process(self, generator: simpy.events.ProcessGenerator) -> simpy.Process:
        return self.env.process(generator)
