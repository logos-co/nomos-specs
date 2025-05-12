from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterator, Optional, TypeAlias

K = 1024
BOOTSTRAP_TIME = timedelta(days=1)
DOWNLOAD_LIMIT = 1000


class Node:
    num_downloadings = 0
    tree: BlockTree

    def run_node(self, peers: list[Node]):
        peers_by_tip = group_peers_by_tip(peers)
        # Determine fork choice rule depending on how long the node has been offline.
        max_peer_tip = max(peers_by_tip.keys(), key=lambda tip: tip.height)
        self.tree.determine_fork_choice(max_peer_tip, self.num_downloadings)

        # In real impl, these downloads should be run in parallel.
        for _, peers in peers_by_tip.items():
            self.download_blocks(peers[0], None)

        # Downloads are done. Listen for new blocks.
        for block, peer in self.listen_for_new_blocks():
            # Determine fork choice depending on how far behind the node is.
            self.tree.determine_fork_choice(block, self.num_downloadings)
            try:
                self.tree.on_block(block)
            except ParentNotFound:
                # Download missing blocks unless they're in a fork behind the latest immutable block.
                if block.height <= self.tree.latest_immutable_block().height:
                    continue
                self.download_blocks(peer, block.id)

    def download_blocks(self, peer: Node, target_block: Optional[BlockId]):
        self.num_downloadings += 1
        try:
            latest_downloaded_block: Optional[Block] = None
            while True:
                # Recreate a request each time:
                # - to download the next batch of blocks.
                # - to handle the case where the peer's honest chain has changed (if target_block is None).
                known_blocks = (
                    [latest_downloaded_block.id] if latest_downloaded_block else []
                )
                known_blocks += [
                    self.tree.tip().id,
                    self.tree.latest_immutable_block().id,
                    self.tree.genesis_block.id,
                ]
                req = DownloadBlocksRequest(
                    target_block,
                    known_blocks,
                )

                num_downloaded_blocks = 0
                for block in peer.handle_download_blocks(req):
                    num_downloaded_blocks += 1
                    latest_downloaded_block = block
                    # Stop downloading if the block is behind the latest immutable block.
                    if block.height <= self.tree.latest_immutable_block().height:
                        return
                    try:
                        self.tree.on_block(block)
                    except Exception:
                        return

                # Downloading is done if the peer returns blocks less than the limit.
                if num_downloaded_blocks < DOWNLOAD_LIMIT:
                    return
        finally:
            self.num_downloadings -= 1

    def listen_for_new_blocks(self) -> Iterator[tuple[Block, Node]]:
        # TODO
        return iter([])

    def tip(self) -> Block:
        return self.tree.tip()

    def handle_download_blocks(self, req: DownloadBlocksRequest) -> Iterator[Block]:
        # TODO
        return iter([])


def group_peers_by_tip(peers: list[Node]) -> dict[Block, list[Node]]:
    peers_by_tip: dict[Block, list[Node]] = defaultdict(list)
    for peer in peers:
        peers_by_tip[peer.tip()].append(peer)
    return peers_by_tip


BlockId: TypeAlias = bytes


@dataclass
class Block:
    id: BlockId
    height: int


@dataclass
class BlockTree:
    fork_choice: ForkChoice
    genesis_block: Block

    def tip(self) -> Block:
        # TODO
        return self.genesis_block

    def latest_immutable_block(self) -> Block:
        # TODO: Require explicit commit.
        # If the fork choice hasn't been switched to ONLINE, no blocks are immutable and we can't rely on K.
        # Also, if the fork choice has been switched from ONLINE to BOOTSTRAP, we can't rely on K.
        return self.genesis_block

    def determine_fork_choice(self, received_block: Block, num_downloadings: int):
        self.fork_choice = self.fork_choice.update(
            received_block.height, self.tip().height, num_downloadings
        )

    def on_block(self, block: Block):
        pass


@dataclass
class ForkChoice:
    rule: ForkChoiceRule
    start_time: datetime

    def update(
        self, received_block_height: int, local_tip_height: int, num_downloadings: int
    ) -> ForkChoice:
        # If the node has been offline while more than K blocks were being created, switch to BOOTSTRAP.
        # It means that the node is behind the k-block of the peer.
        if received_block_height - local_tip_height >= K:
            return ForkChoice(rule=ForkChoiceRule.BOOTSTRAP, start_time=datetime.now())

        # If not, basically keep the current rule.
        # But, if bootstrap time has passed, switch to ONLINE.
        if (
            self.rule == ForkChoiceRule.BOOTSTRAP
            and num_downloadings == 0
            and datetime.now() - self.start_time > BOOTSTRAP_TIME
        ):
            return ForkChoice(rule=ForkChoiceRule.ONLINE, start_time=datetime.now())
        else:
            return self


class ForkChoiceRule(Enum):
    BOOTSTRAP = 1
    ONLINE = 2


class ParentNotFound(Exception):
    pass


@dataclass
class DownloadBlocksRequest:
    target_block: Optional[BlockId]
    known_blocks: list[BlockId]
