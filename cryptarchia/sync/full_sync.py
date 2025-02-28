from collections import defaultdict
from typing import Generator

from cryptarchia.cryptarchia import BlockHeader, Follower, Id, Slot
from cryptarchia.error import ParentNotFound

SLOT_TOLERANCE = 1


def full_sync(
    local: Follower, remotes: list[Follower], start_slot: Slot
) -> list[BlockHeader]:
    # Start a full sync from the remotes to the local, starting from the given slot.
    # Return orphaned blocks that could not be applied to the local.

    # Sync only with remotes that are at least SLOT_TOLERANCE ahead of the local.
    # Continue until there is no target to sync with.
    #
    # Group the remotes by their tip slot, and sync only with one remote per group.
    # This is safe as long as the remote provides all blocks necessary for the future fork choice.
    orphans: list[BlockHeader] = []
    while groups := group_targets(remotes, start_slot):
        for _tip_id, group in groups.items():
            remote = group[0]
            for orphan in range_sync(local, remote, start_slot, remote.tip().slot):
                orphans.append(orphan)
        # Update the start_slot to check if the sync should continue.
        start_slot = Slot(local.tip().slot.absolute_slot + 1)
    return orphans


def range_sync(
    local: Follower, remote: Follower, from_slot: Slot, to_slot: Slot
) -> Generator[BlockHeader, None, None]:
    # Fetch blocks in the given range of slots from the remote and apply them to the local.
    # Blocks should be fetched in order of slot.
    for block in remote.block_storage.blocks_by_range(from_slot, to_slot):
        try:
            local.on_block(block)
        except ParentNotFound:
            yield block
        except:
            raise


def group_targets(
    targets: list[Follower], start_slot: Slot
) -> dict[Id, list[Follower]]:
    # Group the targets by their tip slot.
    # Filter only the targets that are at least SLOT_TOLERANCE ahead of the start_slot.
    groups: dict[Id, list[Follower]] = defaultdict(list)
    for target in targets:
        if target.tip().slot.absolute_slot - start_slot.absolute_slot > SLOT_TOLERANCE:
            groups[target.tip_id()].append(target)
    return groups
