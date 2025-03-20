from .cryptarchia import (
    Config,
    Slot,
    Note,
    BlockHeader,
    LedgerState,
    MockLeaderProof,
    Leader,
    Follower,
    Hash,
)


class TestNode:
    def __init__(self, config: Config, genesis: LedgerState, note: Note):
        self.config = config
        self.leader = Leader(note=note, config=config)
        self.follower = Follower(genesis, config)

    def epoch_state(self, slot: Slot):
        return self.follower.compute_epoch_state(
            slot.epoch(self.config), self.follower.tip_id()
        )

    def on_slot(self, slot: Slot) -> BlockHeader | None:
        parent = self.follower.tip_id()
        epoch_state = self.epoch_state(slot)
        if leader_proof := self.leader.try_prove_slot_leader(epoch_state, slot, parent):
            return BlockHeader(
                parent=parent,
                slot=slot,
                leader_proof=leader_proof,
                content_size=0,
                content_id=bytes(32),
            )
        return None

    def on_block(self, block: BlockHeader):
        self.follower.on_block(block)


def mk_config(initial_stake_distribution: list[Note]) -> Config:
    initial_inferred_total_stake = sum(n.value for n in initial_stake_distribution)
    return Config.cryptarchia_v0_0_1(initial_inferred_total_stake).replace(
        k=1,
        active_slot_coeff=0.5,
    )


def mk_genesis_state(initial_stake_distribution: list[Note]) -> LedgerState:
    return LedgerState(
        block=BlockHeader(
            slot=Slot(0),
            parent=bytes(32),
            content_size=0,
            content_id=bytes(32),
            leader_proof=MockLeaderProof(
                Note(sk=0, value=0), Slot(0), parent=bytes(32)
            ),
        ),
        nonce=bytes(32),
        commitments={n.commitment() for n in initial_stake_distribution},
        nullifiers=set(),
    )


def mk_block(
    parent: BlockHeader, slot: int, note: Note, content=bytes(32)
) -> BlockHeader:
    assert type(parent) == BlockHeader, type(parent)
    assert type(slot) == int, type(slot)

    return BlockHeader(
        slot=Slot(slot),
        parent=parent.id(),
        content_size=len(content),
        content_id=Hash(b"CONTENT_ID", content),
        leader_proof=MockLeaderProof(note, Slot(slot), parent=parent.id()),
    )


def mk_chain(
    parent: BlockHeader, note: Note, slots: list[int]
) -> tuple[list[BlockHeader], Note]:
    assert type(parent) == BlockHeader
    chain = []
    for s in slots:
        block = mk_block(parent=parent, slot=s, note=note)
        chain.append(block)
        parent = block
    return chain
