from __future__ import annotations

from collections import defaultdict
from typing import Generator

from cryptarchia.cryptarchia import (
    BlockHeader,
    Follower,
    Hash,
    LedgerState,
    ParentNotFound,
    Slot,
    iter_chain_blocks,
)


def sync(local: Follower, peers: list[Follower], checkpoint: LedgerState | None = None):
    # Syncs the local block tree with the peers, starting from the local tip.
    # This covers the case where the local tip is not on the latest honest chain anymore.

    block_fetcher = BlockFetcher(peers)

    # If the checkpoint is provided, start backfilling the checkpoint chain in the background.
    # But for simplicity, we do it in the foreground here.
    # If the backfilling fails, it means that the checkpoint chain is invalid,
    # and the sync process should be cancelled.
    if checkpoint:
        backfill_fork(local, checkpoint.block, None, block_fetcher)

    # Repeat the sync process until no peer has a tip ahead of the local tip,
    # because peers' tips may advance during the sync process.
    rejected_blocks: set[Hash] = set()
    while True:
        # Fetch blocks from the peers in the range of slots from the local tip to the latest tip.
        # Gather orphaned blocks, which are blocks from forks that are absent in the local block tree.

        start_slot = local.tip().slot
        orphans: dict[BlockHeader, BlockFetcher.PeerId] = dict()
        num_blocks = 0
        for block, peer_id in block_fetcher.fetch_blocks_from(start_slot):
            num_blocks += 1
            # Reject blocks that have been rejected in the past
            # or whose parent has been rejected.
            if {block.id(), block.parent} & rejected_blocks:
                rejected_blocks.add(block.id())
                continue

            try:
                local.on_block(block)
                orphans.pop(block, None)
            except ParentNotFound:
                orphans[block] = peer_id
            except Exception:
                rejected_blocks.add(block.id())

        # Finish the sync process if no block has been fetched,
        # which means that no peer has a tip ahead of the local tip.
        if num_blocks == 0:
            return

        # Backfill the orphan forks starting from the orphan blocks with applying fork choice rule.
        #
        # Sort the orphan blocks by slot in descending order to minimize the number of backfillings.
        for orphan, peer_id in sorted(orphans.items(), key=lambda item: item[0].slot, reverse=True):
            # Skip the orphan block if it has been processed during the previous backfillings
            # (i.e. if it has been already added to the local block tree).
            # Or, skip if it has been rejected during the previous backfillings.
            if (
                orphan.id() not in local.ledger_state
                and orphan.id() not in rejected_blocks
            ):
                try:
                    backfill_fork(local, orphan, peer_id, block_fetcher)
                except InvalidBlockFromBackfillFork as e:
                    rejected_blocks.update(block.id() for block in e.invalid_suffix)


def backfill_fork(
    local: Follower,
    fork_tip: BlockHeader,
    fork_peer_id: BlockFetcher.PeerId | None,
    block_fetcher: BlockFetcher,
):
    # Backfills a fork, which is absent in the local block tree, by fetching blocks from the peers.
    # During backfilling, the fork choice rule is continuously applied.

    suffix = find_missing_part(
        local,
        block_fetcher.fetch_chain_backward(fork_tip.id(), fork_peer_id),
    )

    # Add blocks in the fork suffix with applying fork choice rule.
    # After all, add the tip of the fork suffix to apply the fork choice rule.
    for i, block in enumerate(suffix):
        try:
            local.on_block(block)
        except Exception as e:
            raise InvalidBlockFromBackfillFork(e, suffix[i:])


def find_missing_part(
    local: Follower, fork: Generator[BlockHeader, None, None]
) -> list[BlockHeader]:
    # Finds the point where the fork is disconnected from the local block tree,
    # and returns the suffix of the fork from the disconnected point to the tip.
    # The disconnected point may be different from the divergence point of the fork
    # in the case where the fork has been partially backfilled.

    suffix: list[BlockHeader] = []
    for block in fork:
        if block.id() in local.ledger_state:
            break
        suffix.append(block)
    suffix.reverse()
    return suffix


class BlockFetcher:
    # NOTE: This class is a mock, which uses a naive approach to fetch blocks from multiple peers.
    # In real implementation, any optimized way can be used, such as parallel fetching.

    PeerId = int

    def __init__(self, peers: list[Follower]):
        self.peers = dict()
        for peer_id, peer in enumerate(peers):
            self.peers[peer_id] = peer

    def fetch_blocks_from(self, start_slot: Slot) -> Generator[tuple[BlockHeader, PeerId], None, None]:
        # Filter peers that have a tip ahead of the local tip
        # and group peers by their tip to minimize the number of fetches.
        # This strategy can be optimized in real implementations.
        groups = self.filter_and_group_peers_by_tip(start_slot)
        for group in groups.values():
            for block, peer_id in BlockFetcher.fetch_blocks_by_slot(group, start_slot):
                yield block, peer_id

    def filter_and_group_peers_by_tip(
        self, start_slot: Slot
    ) -> dict[BlockHeader, dict[PeerId, Follower]]:
        # Group peers by their tip.
        # Filter only the peers whose tip is ahead of the start_slot.
        groups = defaultdict(dict)
        for peer_id, peer in self.peers.items():
            if peer.tip().slot.absolute_slot > start_slot.absolute_slot:
                groups[peer.tip()][peer_id] = peer
        return groups

    @staticmethod
    def fetch_blocks_by_slot(
        peers: dict[PeerId, Follower], start_slot: Slot
    ) -> Generator[tuple[BlockHeader, PeerId], None, None]:
        # Fetch blocks in the given range of slots from one of the peers.
        # Blocks should be returned in order of slot.
        # If a peer fails, try the next peer.
        # This strategy can be optimized in real implementations.
        for peer_id, peer in peers.items():
            try:
                for block in peer.blocks_by_slot(start_slot):
                    yield block, peer_id
                    # Update start_slot for the potential try with the next peer.
                    start_slot = block.slot
                # The peer successfully returned all blocks. No need to try the next peer.
                break
            except Exception:
                continue

    def fetch_chain_backward(
        self, tip: Hash, peer_id: PeerId | None,
    ) -> Generator[BlockHeader, None, None]:
        # Fetches a chain of blocks from a peer, starting from the given tip to the genesis.
        # If peer_id is not set, fetch the chain by querying multiple peers.
        # Fetching from multiple peers can be optimized in real implementations.
        id = tip
        peers = [self.peers[peer_id]] if peer_id is not None else list(self.peers.values())
        for peer in peers:
            for block in iter_chain_blocks(id, peer.ledger_state):
                yield block
                if block.id() == peer.genesis_state.block.id():
                    # Received the entire chain from the peer.
                    # No need to continue with the next peer.
                    return
                id = block.parent


class InvalidBlockFromBackfillFork(Exception):
    def __init__(self, cause: Exception, invalid_suffix: list[BlockHeader]):
        super().__init__()
        self.cause = cause
        self.invalid_suffix = invalid_suffix
