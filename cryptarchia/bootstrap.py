from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Iterator, Optional, TypeAlias

K = 1024
T = timedelta(days=1)
DOWNLOAD_LIMIT = 1000


def run_node(tree: BlockTree, peers: list[Peer]):
    peers_by_tip = group_peers_by_tip(peers)
    # Determine fork choice rule depending on how long the node has been offline.
    max_peer_tip = max(peers_by_tip.keys(), key=lambda tip: tip.height)
    tree.determine_fork_choice(max_peer_tip)

    # In real impl, these downloads should be run in parallel.
    for _, peers in peers_by_tip.items():
        download_blocks(tree, peers[0], None)

    # Downloads are done. Listen for new blocks.
    for block, peer in listen_for_new_blocks():
        # Determine fork choice depending on how far behind the node is.
        tree.determine_fork_choice(block)
        try:
            tree.on_block(block)
        except ParentNotFound:
            if block.height <= tree.latest_immutable_block().height:
                continue
            download_blocks(tree, peer, block.id)


def group_peers_by_tip(peers: list[Peer]) -> dict[Block, list[Peer]]:
    peers_by_tip: dict[Block, list[Peer]] = defaultdict(list)
    for peer in peers:
        peers_by_tip[peer.tip()].append(peer)
    return peers_by_tip


def download_blocks(tree: BlockTree, peer: Peer, target_block: Optional[BlockId]):
    latest_downloaded_block: Optional[Block] = None
    while True:
        # Recreate a request each time:
        # - to download the next batch of blocks.
        # - to handle the case where the peer's honest chain has changed (if target_block is None).
        known_blocks = [latest_downloaded_block.id] if latest_downloaded_block else []
        known_blocks += [
            tree.tip().id,
            tree.latest_immutable_block().id,
            tree.genesis_block.id,
        ]
        req = DownloadBlocksRequest(
            target_block,
            known_blocks,
        )

        num_downloaded = 0
        for block in peer.download_blocks(req):
            num_downloaded += 1
            latest_downloaded_block = block
            if block.height <= tree.latest_immutable_block().height:
                return
            try:
                tree.on_block(block)
            except Exception:
                return

        if num_downloaded < DOWNLOAD_LIMIT:
            return


def listen_for_new_blocks() -> Iterator[tuple[Block, Peer]]:
    # TODO
    return iter([])


@dataclass
class Peer:
    tree: BlockTree

    def tip(self) -> Block:
        return self.tree.tip()

    def download_blocks(self, req: DownloadBlocksRequest) -> Iterator[Block]:
        # TODO
        return iter([])


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

    def determine_fork_choice(self, received_block: Block):
        self.fork_choice = self.fork_choice.update(
            received_block.height, self.tip().height
        )

    def on_block(self, block: Block):
        pass


@dataclass
class ForkChoice:
    rule: ForkChoiceRule
    start_time: datetime

    def update(self, received_block_height: int, local_tip_height: int) -> ForkChoice:
        # If the node has been offline while more than K blocks were being created, switch to BOOTSTRAP.
        # It means that the node is behind the k-block of the peer.
        if received_block_height - local_tip_height >= K:
            return ForkChoice(rule=ForkChoiceRule.BOOTSTRAP, start_time=datetime.now())

        # If not, basically keep the current rule.
        # But, if bootstrap time has passed, switch to ONLINE.
        if (
            self.rule == ForkChoiceRule.BOOTSTRAP
            and datetime.now() - self.start_time > T
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
