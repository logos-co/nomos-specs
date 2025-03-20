from collections import defaultdict
from typing import Generator

from cryptarchia.cryptarchia import (
    BlockHeader,
    Follower,
    Hash,
    ParentNotFound,
    Slot,
    common_prefix_depth_from_chains,
    iter_chain_blocks,
)


def sync(local: Follower, peers: list[Follower]):
    # Syncs the local block tree with the peers, starting from the local tip.
    # This covers the case where the local tip is not on the latest honest chain anymore.

    # Repeat the sync process until no peer has a tip ahead of the local tip,
    # because peers' tips may advance during the sync process.
    block_fetcher = BlockFetcher(peers)
    rejected_blocks: set[Hash] = set()
    while True:
        # Fetch blocks from the peers in the range of slots from the local tip to the latest tip.
        # Gather orphaned blocks, which are blocks from forks that are absent in the local block tree.

        start_slot = local.tip().slot
        orphans: set[BlockHeader] = set()
        num_blocks = 0
        for block in block_fetcher.fetch_blocks_from(start_slot):
            num_blocks += 1
            # Reject blocks that have been rejected in the past
            # or whose parent has been rejected.
            if {block.id(), block.parent} & rejected_blocks:
                rejected_blocks.add(block.id())
                continue

            try:
                local.on_block(block)
                orphans.discard(block)
            except ParentNotFound:
                orphans.add(block)
            except Exception:
                rejected_blocks.add(block.id())

        # Finish the sync process if no block has been fetched,
        # which means that no peer has a tip ahead of the local tip.
        if num_blocks == 0:
            return

        # Backfill the orphan forks starting from the orphan blocks with applying fork choice rule.
        #
        # Sort the orphan blocks by slot in descending order to minimize the number of backfillings.
        for orphan in sorted(orphans, key=lambda b: b.slot, reverse=True):
            # Skip the orphan block if it has been processed during the previous backfillings
            # (i.e. if it has been already added to the local block tree).
            # Or, skip if it has been rejected during the previous backfillings.
            if (
                orphan.id() not in local.ledger_state
                and orphan.id() not in rejected_blocks
            ):
                try:
                    backfill_fork(local, orphan, block_fetcher)
                except InvalidBlockFromBackfillFork as e:
                    rejected_blocks.update(block.id() for block in e.invalid_suffix)


def backfill_fork(
    local: Follower,
    fork_tip: BlockHeader,
    block_fetcher: "BlockFetcher",
):
    # Backfills a fork, which is absent in the local block tree, by fetching blocks from the peers.
    # During backfilling, the fork choice rule is continuously applied.
    #
    # If necessary, the local honest chain is also backfilled for the fork choice rule.
    # This can happen if the honest chain has been built not from the genesis (i.e. checkpoint sync).

    _, tip_suffix, _, fork_suffix = common_prefix_depth_from_chains(
        block_fetcher.fetch_chain_backward(local.tip_id(), local),
        block_fetcher.fetch_chain_backward(fork_tip.id(), local),
    )

    # First, backfill the local honest chain if some blocks are missing.
    # In other words, backfill the local block tree, which contains the honest chain.
    for block in tip_suffix:
        try:
            # Just apply the block to the ledger state is enough
            # instead of calling `on_block` which runs the fork choice rule.
            local.apply_block_to_ledger_state(block)
        except Exception as e:
            raise InvalidBlockTree(e)

    # Then, add blocks in the fork suffix with applying fork choice rule.
    # After all, add the tip of the fork suffix to apply the fork choice rule.
    for i, block in enumerate(fork_suffix):
        try:
            local.on_block(block)
        except Exception as e:
            raise InvalidBlockFromBackfillFork(e, fork_suffix[i:])


class BlockFetcher:
    # NOTE: This class is a mock, which uses a naive approach to fetch blocks from multiple peers.
    # In real implementation, any optimized way can be used, such as parallel fetching.

    def __init__(self, peers: list[Follower]):
        self.peers = peers

    def fetch_blocks_from(self, start_slot: Slot) -> Generator[BlockHeader, None, None]:
        # Filter peers that have a tip ahead of the local tip
        # and group peers by their tip to minimize the number of fetches.
        groups = self.filter_and_group_peers_by_tip(start_slot)
        for group in groups.values():
            for block in BlockFetcher.fetch_blocks_by_slot(group, start_slot):
                yield block

    def filter_and_group_peers_by_tip(
        self, start_slot: Slot
    ) -> dict[BlockHeader, list[Follower]]:
        # Group peers by their tip.
        # Filter only the peers whose tip is ahead of the start_slot.
        groups: dict[BlockHeader, list[Follower]] = defaultdict(list)
        for peer in self.peers:
            if peer.tip().slot.absolute_slot > start_slot.absolute_slot:
                groups[peer.tip()].append(peer)
        return groups

    @staticmethod
    def fetch_blocks_by_slot(
        peers: list[Follower], start_slot: Slot
    ) -> Generator[BlockHeader, None, None]:
        # Fetch blocks in the given range of slots from one of the peers.
        # Blocks should be returned in order of slot.
        # If a peer fails, try the next peer.
        for peer in peers:
            try:
                for block in peer.blocks_by_slot(start_slot):
                    yield block
                    # Update start_slot for the potential try with the next peer.
                    start_slot = block.slot
                # The peer successfully returned all blocks. No need to try the next peer.
                break
            except Exception:
                continue

    def fetch_chain_backward(
        self, tip: Hash, local: Follower
    ) -> Generator[BlockHeader, None, None]:
        # Fetches a chain of blocks from the peers, starting from the given tip to the genesis.
        # Attempts to extend the chain as much as possible by querying multiple peers,
        # considering that not all peers may have the full chain (from the genesis).

        id = tip
        # First, try to iterate the chain from the local block tree.
        for block in iter_chain_blocks(id, local.ledger_state):
            yield block
            if block.id() == local.genesis_state.block.id():
                return
            id = block.parent

        # Try to continue by fetching the remaining blocks from the peers
        for peer in self.peers:
            for block in iter_chain_blocks(id, peer.ledger_state):
                yield block
                if block.id() == local.genesis_state.block.id():
                    return
                id = block.parent


class InvalidBlockTree(Exception):
    def __init__(self, cause: Exception):
        super().__init__()
        self.cause = cause


class InvalidBlockFromBackfillFork(Exception):
    def __init__(self, cause: Exception, invalid_suffix: list[BlockHeader]):
        super().__init__()
        self.cause = cause
        self.invalid_suffix = invalid_suffix
