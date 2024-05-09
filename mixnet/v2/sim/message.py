from __future__ import annotations


class Message:
    def __init__(self, pubkeys: list[bytes], attachments: list[bytes], payload: bytes):
        assert len(pubkeys) == len(attachments)
        eph_sk, eph_pk = bytes(32), bytes(32)  # TODO: use a random x25519 key
        node_keys = Message.node_keys(eph_pk, pubkeys)
        self.header = Header(eph_sk, node_keys, attachments)
        self.payload = payload  # TODO: encrypt payload

    def __bytes__(self):
        return bytes(self.header) + self.payload

    @classmethod
    def node_keys(cls, eph_sk: bytes, pubkeys: list[bytes]) -> list[bytes]:
        return [cls.key_exchange(eph_sk, pk) for pk in pubkeys]

    @classmethod
    def key_exchange(cls, eph_sk, pubkey) -> bytes:
        pass

    # TODO: implement unwrapping the message


class Header:
    DUMMY_MAC = bytes(16)

    def __init__(self, eph_sk: bytes, node_keys: list[bytes], attachments: list[bytes]):
        assert len(node_keys) == len(attachments)
        self.eph_sk = eph_sk
        # TODO: encapsulation
        self.attachments = attachments

    def __bytes__(self):
        return b"".join([self.eph_sk] + [bytes(att) + self.DUMMY_MAC for att in self.attachments])