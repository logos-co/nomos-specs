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
        # Determine fork choice rule depending on how much the node has fallen behind.
        max_peer_tip = max(peers_by_tip.keys(), key=lambda tip: tip.height)
        if max_peer_tip.height - self.tree.tip().height >= K:
            self.tree.fork_choice = ForkChoice(ForkChoiceRule.BOOTSTRAP)
        else:
            self.tree.fork_choice = ForkChoice(ForkChoiceRule.ONLINE)

        # In real impl, these downloads should be run in parallel.
        for _, peers in peers_by_tip.items():
            self.download_blocks(peers[0], None)

        # Downloads are done. Listen for new blocks.
        for block, peer in self.listen_for_new_blocks():
            # Switch fork choice to ONLINE if possible.
            if (
                self.tree.fork_choice.rule == ForkChoiceRule.BOOTSTRAP
                and self.num_downloadings == 0
                and self.tree.fork_choice.elapsed() > BOOTSTRAP_TIME
            ):
                self.tree.fork_choice = ForkChoice(ForkChoiceRule.ONLINE)

            # Try to validate and add the block to the tree.
            try:
                self.tree.on_block(block)
            except InvalidBlock:
                continue
            except ParentNotFound:
                # Download missing blocks unless they're in a fork behind the latest immutable block.
                if block.height <= self.tree.latest_immutable_block().height:
                    continue
                # Switch (reset) to BOOTSTRAP fork choice if the node has fallen behind too much.
                if block.height - self.tree.tip().height >= K:
                    self.tree.fork_choice = ForkChoice(ForkChoiceRule.BOOTSTRAP)
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

    def on_block(self, block: Block):
        pass


@dataclass
class ForkChoice:
    rule: ForkChoiceRule
    start_time: datetime

    def __init__(self, rule: ForkChoiceRule):
        self.rule = rule
        self.start_time = datetime.now()

    def elapsed(self) -> timedelta:
        return datetime.now() - self.start_time


class ForkChoiceRule(Enum):
    BOOTSTRAP = 1
    ONLINE = 2


class InvalidBlock(Exception):
    pass


class ParentNotFound(Exception):
    pass


@dataclass
class DownloadBlocksRequest:
    target_block: Optional[BlockId]
    known_blocks: list[BlockId]
