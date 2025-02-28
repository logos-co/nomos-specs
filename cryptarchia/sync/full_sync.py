from collections import defaultdict
from typing import Generator

from cryptarchia.cryptarchia import BlockHeader, Follower, Id, Slot

SLOT_TOLERANCE = 1


def full_sync(local: Follower, remotes: list[Follower], start_slot: Slot):
    while groups := group_sync_targets(remotes, start_slot):
        for _, group in groups.items():
            remote = group[0]
            range_sync(local, remote, start_slot, remote.tip().slot)
        start_slot = Slot(local.tip().slot.absolute_slot + 1)


def range_sync(local: Follower, remote: Follower, from_slot: Slot, to_slot: Slot):
    for block in request_blocks_by_range(remote, from_slot, to_slot):
        local.on_block(block)


def group_sync_targets(
    targets: list[Follower], start_slot: Slot
) -> dict[Id, list[Follower]]:
    groups: dict[Id, list[Follower]] = defaultdict(list)
    for target in targets:
        if target.tip().slot.absolute_slot - start_slot.absolute_slot > SLOT_TOLERANCE:
            groups[target.tip_id()].append(target)
    return groups


def request_blocks_by_range(
    remote: Follower, from_slot: Slot, to_slot: Slot
) -> Generator[BlockHeader, None, None]:
    # TODO: Optimize this by keeping blocks by slot in the Follower
    blocks_by_slot: dict[int, list[BlockHeader]] = defaultdict(list)
    for ledger_state in remote.ledger_state.values():
        if from_slot <= ledger_state.block.slot <= to_slot:
            blocks_by_slot[ledger_state.block.slot.absolute_slot].append(
                ledger_state.block
            )
    for slot in range(from_slot.absolute_slot, to_slot.absolute_slot + 1):
        for block in blocks_by_slot[slot]:
            yield block
