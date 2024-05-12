from __future__ import annotations

from copy import deepcopy

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PublicKey, X25519PrivateKey


class SphinxPacket:
    def __init__(self, public_keys: list[X25519PublicKey], attachments: list[Attachment], payload: bytes):
        assert len(public_keys) == len(attachments)
        ephemeral_private_key = X25519PrivateKey.generate()
        ephemeral_public_key = ephemeral_private_key.public_key()
        shared_keys = [SharedSecret(ephemeral_private_key, pk) for pk in public_keys]
        self.header = SphinxHeader(ephemeral_public_key, shared_keys, attachments)
        self.payload = payload  # TODO: encrypt payload

    def __bytes__(self):
        return bytes(self.header) + self.payload

    def size(self) -> int:
        return len(bytes(self))

    def unwrap(self, private_key: X25519PrivateKey) -> tuple[SphinxPacket, Attachment]:
        packet = deepcopy(self)
        attachment = packet.header.unwrap_inplace(private_key)
        # TODO: decrypt packet.payload
        return packet, attachment

    def is_all_unwrapped(self) -> bool:
        return self.header.is_all_unwrapped()


class SphinxHeader:
    DUMMY_MAC = b'\xFF' * 16

    def __init__(self, ephemeral_public_key: X25519PublicKey, shared_keys: list[SharedSecret],
                 attachments: list[Attachment]):
        assert len(shared_keys) == len(attachments)
        self.ephemeral_public_key = ephemeral_public_key.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        self.attachments = attachments  # TODO: encapsulation using node_keys

    def __bytes__(self):
        return b"".join([self.ephemeral_public_key] + [bytes(att) + self.DUMMY_MAC for att in self.attachments])

    def unwrap_inplace(self, private_key: X25519PrivateKey) -> Attachment:
        # TODO: shared_secret = SharedSecret(private_key, header.ephemeral_public_key)
        attachment = self.attachments.pop(0)
        self.attachments.append(Attachment(bytes(len(bytes(attachment)))))  # append a dummy attachment
        return attachment

    def is_all_unwrapped(self) -> bool:
        # true if the first attachment is a dummy
        return self.attachments[0] == Attachment(bytes(len(bytes(self.attachments[0]))))


class SharedSecret:
    def __init__(self, private_key: X25519PrivateKey, public_key: X25519PublicKey):
        self.key = private_key.exchange(public_key)  # 32 bytes

    def __bytes__(self):
        return self.key


class Attachment:
    def __init__(self, data: bytes):
        self.data = data

    def __bytes__(self):
        return self.data

    def __eq__(self, other):
        return bytes(self) == bytes(other)