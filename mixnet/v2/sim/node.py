import random

import simpy
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey

from config import Config
from sphinx import SphinxPacket, Attachment
from p2p import P2p


class Node:
    INCENTIVE_TX_SIZE = 512
    REAL_PAYLOAD = b"BLOCK"
    COVER_PAYLOAD = b"COVER"
    PADDING_SEPARATOR = b'\x01'

    def __init__(self, id: int, env: simpy.Environment, p2p: P2p, config: Config):
        self.id = id
        self.env = env
        self.p2p = p2p
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        self.config = config
        self.action = self.env.process(self.send_message())

    def send_message(self):
        """
        Creates/encapsulate a message and send it to the network through the mixnet
        """
        while True:
            yield self.env.timeout(self.config.message_interval)

            payload = self.payload_to_send()
            if payload is None:  # nothing to send in this turn
                continue

            prep_time = random.uniform(0, self.config.max_message_prep_time)
            yield self.env.timeout(prep_time)

            self.log("Sending a message to the mixnet")
            msg = self.create_message(payload)
            self.env.process(self.p2p.broadcast(self, msg))

    def payload_to_send(self) -> bytes | None:
        rnd = random.random()
        if rnd < self.config.real_message_prob:
            return self.REAL_PAYLOAD
        elif rnd < self.config.real_message_prob + self.config.cover_message_prob:
            return self.COVER_PAYLOAD
        else:
            return None

    def create_message(self, payload: bytes) -> SphinxPacket:
        """
        Creates a message using the Sphinx format
        @return:
        """
        mixes = self.p2p.get_nodes(self.config.num_mix_layers)
        public_keys = [mix.public_key for mix in mixes]
        # TODO: replace with realistic tx
        incentive_txs = [Node.create_incentive_tx(mix.public_key) for mix in mixes]
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
                        self.env.process(self.p2p.broadcast(self, final_padded_msg))
                    else:
                        self.log("Dropping a cover message: %s" % msg.payload)
                else:
                    # TODO: use Poisson delay or something else
                    yield self.env.timeout(random.randint(0, 5))
                    self.env.process(self.p2p.broadcast(self, msg))
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