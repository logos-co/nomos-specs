import random

import simpy

from mixnet.v2.sim.message import Message
from mixnet.v2.sim.p2p import P2p


class Node:
    N_MIXES_IN_PATH = 3

    def __init__(self, id: str, env: simpy.Environment, p2p: P2p):
        self.id = id
        self.env = env
        self.p2p = p2p
        self.pubkey = bytes(32)  # TODO: replace with actual x25519 pubkey
        self.action = self.env.process(self.send_message())

    def send_message(self):
        """
        Creates/encapsulate a message and send it to the network through the mixnet
        """
        while True:
            msg = self.create_message()
            yield self.env.timeout(2)
            print("Sending a message at time %d" % self.env.now)
            self.env.process(self.p2p.broadcast(msg))

    def create_message(self) -> bytes:
        """
        Creates a message using the Sphinx format
        @return:
        """
        mixes = self.p2p.get_nodes(self.N_MIXES_IN_PATH)
        incentive_txs = [bytes(256) for _ in mixes]  # TODO: replace with realistic tx
        msg = Message(mixes, incentive_txs, b"Hello, world!")
        return bytes(msg)

    def receive_message(self, msg: bytes):
        """
        Receives a message from the network, processes it,
        and forwards it to the next mix or the entire network if necessary.
        @param msg: the message to be processed
        """
        yield self.env.timeout(random.randint(0,3))
        print("Receiving a message at time %d" % self.env.now)
        # TODO: this is a dummy logic
        # if msg[0] == 0x00:  # if the msg is to be relayed
        #     if msg[1] == 0x00:  # if I'm the exit mix,
        #         self.env.process(self.p2p.broadcast(msg))
        #     else: # Even if not, forward it to the next mix
        #         yield self.env.timeout(1)  # TODO: use a random delay
        #         # Use broadcasting here too
        #         self.env.process(self.p2p.broadcast(msg))
        # else:  # if the msg has gone through all mixes
        #     pass
