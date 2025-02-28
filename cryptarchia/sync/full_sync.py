from collections import defaultdict

from cryptarchia.cryptarchia import Follower, Id, Slot

SLOT_TOLERANCE = 1


def full_sync(local: Follower, remotes: list[Follower], start_slot: Slot):
    while groups := group_targets(remotes, start_slot):
        for _, group in groups.items():
            remote = group[0]
            range_sync(local, remote, start_slot, remote.tip().slot)
        start_slot = Slot(local.tip().slot.absolute_slot + 1)


def range_sync(local: Follower, remote: Follower, from_slot: Slot, to_slot: Slot):
    for block in remote.block_storage.blocks_by_range(from_slot, to_slot):
        local.on_block(block)


def group_targets(
    targets: list[Follower], start_slot: Slot
) -> dict[Id, list[Follower]]:
    groups: dict[Id, list[Follower]] = defaultdict(list)
    for target in targets:
        if target.tip().slot.absolute_slot - start_slot.absolute_slot > SLOT_TOLERANCE:
            groups[target.tip_id()].append(target)
    return groups
