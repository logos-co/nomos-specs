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
        packet, route = SphinxPacketBuilder.build(msg, global_config, 3)
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

    def test_max_message_size(self):
        global_config, _, _ = init_mixnet_config(10, max_message_size=2000)
        mix_path_length = global_config.max_mix_path_length

        packet1, _ = SphinxPacketBuilder.build(
            self.random_bytes(1500), global_config, mix_path_length
        )
        packet2, _ = SphinxPacketBuilder.build(
            self.random_bytes(2000), global_config, mix_path_length
        )
        self.assertEqual(len(packet1.bytes()), len(packet2.bytes()))

        msg = self.random_bytes(2001)
        with self.assertRaises(ValueError):
            _ = SphinxPacketBuilder.build(msg, global_config, mix_path_length)

    def test_max_mix_path_length(self):
        global_config, _, _ = init_mixnet_config(10, max_mix_path_length=2)
        msg = self.random_bytes(global_config.max_message_size)

        packet1, _ = SphinxPacketBuilder.build(msg, global_config, 1)
        packet2, _ = SphinxPacketBuilder.build(msg, global_config, 2)
        self.assertEqual(len(packet1.bytes()), len(packet2.bytes()))

        with self.assertRaises(ValueError):
            _ = SphinxPacketBuilder.build(msg, global_config, 3)

    @staticmethod
    def random_bytes(size: int) -> bytes:
        assert size >= 0
        return bytes([randint(0, 255) for _ in range(size)])
