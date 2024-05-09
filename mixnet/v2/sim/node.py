from mixnet.v2.sim.simulation import Simulation


class Node:
    def __init__(self, sim: Simulation):
        self.sim = sim
        self.sim.env.process(self.send_message())

    def send_message(self):
        """
        Creates/encapsulate a message and send it to the network through the mixnet
        """
        while True:
            msg = self.create_message()
            yield self.sim.env.timeout(3)
            self.sim.env.process(self.sim.p2p.broadcast(msg))

    def create_message(self) -> bytes:
        """
        Creates a message using the Sphinx format
        @return:
        """
        return b""

    def receive_message(self, msg: bytes):
        """
        Receives a message from the network, processes it,
        and forwards it to the next mix or the entire network if necessary.
        @param msg: the message to be processed
        """
        # TODO: this is a dummy logic
        if msg[0] == 0x00:  # if the msg is to be relayed
            if msg[1] == 0x00:  # if I'm the exit mix,
                self.sim.env.process(self.sim.p2p.broadcast(msg))
            else: # Even if not, forward it to the next mix
                yield self.sim.env.timeout(1)  # TODO: use a random delay
                # Use broadcasting here too
                self.sim.env.process(self.sim.p2p.broadcast(msg))
        else:  # if the msg has gone through all mixes
            pass
