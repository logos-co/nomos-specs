import random
from dataclasses import dataclass

import simpy
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey

from sphinx import SphinxPacket, Attachment
from p2p import P2p


class Node:
    INCENTIVE_TX_SIZE = 512
    REAL_PAYLOAD = b"BLOCK"
    COVER_PAYLOAD = b"COVER"
    PADDING_SEPARATOR = b'\x01'

    @dataclass
    class Parameters:
        num_mix_layers: int
        message_interval: int
        message_prob: float
        max_message_prep_time: int


    def __init__(self, id: int, env: simpy.Environment, p2p: P2p, params: Parameters):
        self.id = id
        self.env = env
        self.p2p = p2p
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.params = params
        self.action = self.env.process(self.send_message())

    def send_message(self):
        """
        Creates/encapsulate a message and send it to the network through the mixnet
        """
        while True:
            msg = self.create_message()
            # TODO: Use the realistic cover traffic emission rate
            yield self.env.timeout(2)
            self.log("Sending a message to the mixnet")
            self.env.process(self.p2p.broadcast(msg))

    def create_message(self) -> SphinxPacket:
        """
        Creates a message using the Sphinx format
        @return:
        """
        mixes = self.p2p.get_nodes(self.params.num_mix_layers)
        public_keys = [mix.public_key for mix in mixes]
        # TODO: replace with realistic tx
        incentive_txs = [Node.create_incentive_tx(mix.public_key) for mix in mixes]
        payload = random.choice([self.REAL_PAYLOAD, self.COVER_PAYLOAD])
        return SphinxPacket(public_keys, incentive_txs, payload)

    def receive_message(self, msg: SphinxPacket | bytes):
        """
        Receives a message from the network, processes it,
        and forwards it to the next mix or the entire network if necessary.
        @param msg: the message to be processed
        """
        # simulating network latency
        yield self.env.timeout(random.randint(0, 3))

        if isinstance(msg, SphinxPacket):
            msg, incentive_tx = msg.unwrap(self.private_key)
            if self.is_my_incentive_tx(incentive_tx):
                self.log("Receiving SphinxPacket. It's mine!")
                if msg.is_all_unwrapped():
                    if msg.payload == self.REAL_PAYLOAD:
                        # Pad the final msg to the same size as a SphinxPacket,
                        # assuming that the final msg is going to be sent via secure channels (TLS, Noise, etc.)
                        final_padded_msg = (msg.payload
                                            + self.PADDING_SEPARATOR
                                            + bytes(len(msg) - len(msg.payload) - len(self.PADDING_SEPARATOR)))
                        self.env.process(self.p2p.broadcast(final_padded_msg))
                else:
                    # TODO: use Poisson delay or something else
                    yield self.env.timeout(random.randint(0, 5))
                    self.env.process(self.p2p.broadcast(msg))
            else:
                self.log("Receiving SphinxPacket, but not mine")
        else:
            final_msg = msg[:msg.rfind(self.PADDING_SEPARATOR)]
            self.log("Received final message: %s" % final_msg)

    # TODO: This is a dummy logic
    @classmethod
    def create_incentive_tx(cls, mix_public_key: X25519PublicKey) -> Attachment:
        public_key = mix_public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        public_key += bytes(cls.INCENTIVE_TX_SIZE - len(public_key))
        return Attachment(public_key)

    def is_my_incentive_tx(self, tx: Attachment) -> bool:
        return tx == Node.create_incentive_tx(self.public_key)

    def log(self, msg):
        print("Node:%d at %g: %s" % (self.id, self.env.now, msg))