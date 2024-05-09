import simpy


class Simulation:
    def __init__(self):
        self.env = simpy.Environment()
        self.p2p = None  # TODO: implement p2p

    def run(self, until):
        self.env.run(until=until)
