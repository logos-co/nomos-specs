from __future__ import annotations

from typing import List, Tuple

from pysphinx.sphinx import SphinxPacket

from mixnet.config import GlobalConfig, NodeInfo


class SphinxPacketBuilder:
    @staticmethod
    def build(
        message: bytes, global_config: GlobalConfig, path_len: int
    ) -> Tuple[SphinxPacket, List[NodeInfo]]:
        if path_len <= 0:
            raise ValueError("path_len must be greater than 0")
        if len(message) > global_config.max_message_size:
            raise ValueError("message is too long")

        route = global_config.membership.generate_route(path_len)
        # We don't need the destination (defined in the Loopix Sphinx spec)
        # because the last mix will broadcast the fully unwrapped message.
        # Later, we will optimize the Sphinx according to our requirements.
        dummy_destination = route[-1]

        packet = SphinxPacket.build(
            message,
            route=[mixnode.sphinx_node() for mixnode in route],
            destination=dummy_destination.sphinx_node(),
            max_route_length=global_config.max_mix_path_length,
            max_plain_payload_size=global_config.max_message_size,
        )
        return (packet, route)
