from cryptarchia.cryptarchia import Follower, LedgerState, iter_chain
from cryptarchia.sync.full_sync import full_sync


def get_checkpoint(follower: Follower) -> LedgerState:
    iter = iter_chain(follower.tip_id(), follower.ledger_state)
    for _ in range(follower.config.k):
        next(iter)
    return next(iter)


def checkpoint_sync(local: Follower, checkpoint: LedgerState, remotes: list[Follower]):
    # apply the checkpoint to the local
    checkpoint_block_id = checkpoint.block.id()
    local.ledger_state[checkpoint_block_id] = checkpoint
    local.local_chain = checkpoint_block_id
    local.forks.remove(checkpoint_block_id)
    local.block_storage.add_block(checkpoint.block)

    # start forwards sync from the checkpoint
    orphans = full_sync(local, remotes, local.tip().slot)
    if orphans:
        raise NotImplementedError("Orphaned blocks after checkpoint sync")
