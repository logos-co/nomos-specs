from collections import defaultdict
from typing import Generator

from cryptarchia.cryptarchia import (
    BlockHeader,
    Follower,
    Id,
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
    while True:
        # Fetch blocks from the peers in the range of slots from the local tip to the latest tip.
        # Gather orphaned blocks, which are blocks from forks that are absent in the local block tree.
        start_slot = local.tip().slot
        orphans: set[BlockHeader] = set()
        # Filter and group peers by their tip to minimize the number of fetches.
        groups = filter_and_group_peers_by_tip(peers, start_slot)
        if len(groups) == 0:  # No peer has a tip ahead of the local tip.
            return

        for group in groups.values():
            for block in fetch_blocks_by_slot(group, start_slot):
                try:
                    local.on_block(block)
                    orphans.discard(block)
                except ParentNotFound:
                    orphans.add(block)

        # Backfill the orphan forks starting from the orphan blocks with applying fork choice rule.
        #
        # Sort the orphan blocks by slot in descending order to minimize the number of backfillings.
        for orphan in sorted(orphans, key=lambda b: b.slot, reverse=True):
            # Skip the orphan block processed during the previous backfillings.
            if orphan not in local.ledger_state:
                backfill_fork(local, peers, orphan)


def filter_and_group_peers_by_tip(
    peers: list[Follower], start_slot: Slot
) -> dict[BlockHeader, list[Follower]]:
    # Group peers by their tip.
    # Filter only the peers whose tip is ahead of the start_slot.
    groups: dict[BlockHeader, list[Follower]] = defaultdict(list)
    for peer in peers:
        if peer.tip().slot.absolute_slot > start_slot.absolute_slot:
            groups[peer.tip()].append(peer)
    return groups


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


def backfill_fork(local: Follower, peers: list[Follower], fork_tip: BlockHeader):
    # Backfills a fork, which is absent in the local block tree, by fetching blocks from the peers.
    # During backfilling, the fork choice rule is continuously applied.
    #
    # If necessary, the local honest chain is also backfilled for the fork choice rule.
    # This can happen if the honest chain has been built not from the genesis
    # (e.g. checkpoint sync, or a partially backfilled chain).

    _, tip_suffix, _, fork_suffix = common_prefix_depth_from_chains(
        fetch_chain_blocks(local.tip_id(), local, peers),
        fetch_chain_blocks(fork_tip.id(), local, peers),
    )

    # First, backfill the local honest chain if some blocks are missing.
    # Just applying the blocks to the ledger state is enough,
    # instead of calling `on_block` which updates the tip (by fork choice).
    # because we're just backfilling the old part of the current tip.
    for block in tip_suffix:
        local.apply_block_to_ledger_state(block)

    # Then, process blocks in the fork suffix by applying fork choice rule.
    for block in fork_suffix:
        local.on_block(block)


def fetch_chain_blocks(
    tip: Id, local: Follower, peers: list[Follower]
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
    for peer in peers:
        for block in iter_chain_blocks(id, peer.ledger_state):
            yield block
            if block.id() == local.genesis_state.block.id():
                return
            id = block.parent
