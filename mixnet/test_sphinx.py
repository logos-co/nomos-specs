from random import randint
from typing import cast
from unittest import TestCase

from pysphinx.sphinx import (
    ProcessedFinalHopPacket,
    ProcessedForwardHopPacket,
)

from mixnet.sphinx import SphinxPacketBuilder
from mixnet.test_utils import init_mixnet_config


class TestSphinxPacketBuilder(TestCase):
    def test_builder(self):
        global_config, _, key_map = init_mixnet_config(10)
        msg = self.random_bytes(500)
        packet, route = SphinxPacketBuilder.build(msg, global_config.membership, 3)
        self.assertEqual(3, len(route))

        processed = packet.process(key_map[route[0].public_key.public_bytes_raw()])
        self.assertIsInstance(processed, ProcessedForwardHopPacket)
        processed = cast(ProcessedForwardHopPacket, processed).next_packet.process(
            key_map[route[1].public_key.public_bytes_raw()]
        )
        self.assertIsInstance(processed, ProcessedForwardHopPacket)
        processed = cast(ProcessedForwardHopPacket, processed).next_packet.process(
            key_map[route[2].public_key.public_bytes_raw()]
        )
        self.assertIsInstance(processed, ProcessedFinalHopPacket)
        recovered = cast(
            ProcessedFinalHopPacket, processed
        ).payload.recover_plain_playload()
        self.assertEqual(msg, recovered)

    @staticmethod
    def random_bytes(size: int) -> bytes:
        assert size >= 0
        return bytes([randint(0, 255) for _ in range(size)])
