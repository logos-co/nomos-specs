from collections import defaultdict
from typing import Generator

from dill.tests.test_diff import A

from cryptarchia.cryptarchia import BlockHeader, Follower, Id, Slot

SLOT_TOLERANCE = 2


def range_sync(local: Follower, remotes: list[Follower], start_slot: Slot):
    while groups := {
        tip: group
        for tip, group in group_by_tip(remotes).items()
        if group[0].tip().slot.absolute_slot - start_slot.absolute_slot > SLOT_TOLERANCE
    }:
        for _, group in groups.items():
            remote = group[0]
            for block in request_blocks_by_range(remote, start_slot, remote.tip().slot):
                local.on_block(block)
        start_slot = Slot(local.tip().slot.absolute_slot + 1)


def group_by_tip(remotes: list[Follower]) -> dict[Id, list[Follower]]:
    groups: dict[Id, list[Follower]] = defaultdict(list)
    for remote in remotes:
        groups[remote.tip_id()].append(remote)
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
