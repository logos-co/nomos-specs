from .cryptarchia import (
    Config,
    Slot,
    Coin,
    BlockHeader,
    LedgerState,
    MockLeaderProof,
    Leader,
    Follower,
)


class TestNode:
    def __init__(self, config: Config, genesis: LedgerState, coin: Coin):
        self.config = config
        self.leader = Leader(coin=coin, config=config)
        self.follower = Follower(genesis, config)

    def epoch_state(self, slot: Slot):
        return self.follower.compute_epoch_state(
            slot.epoch(self.config), self.follower.tip_id()
        )

    def on_slot(self, slot: Slot) -> BlockHeader | None:
        parent = self.follower.tip_id()
        epoch_state = self.epoch_state(slot)
        if leader_proof := self.leader.try_prove_slot_leader(epoch_state, slot, parent):
            self.leader.coin = self.leader.coin.evolve()
            return BlockHeader(
                parent=parent,
                slot=slot,
                orphaned_proofs=self.follower.unimported_orphans(),
                leader_proof=leader_proof,
                content_size=0,
                content_id=bytes(32),
            )
        return None

    def on_block(self, block: BlockHeader):
        self.follower.on_block(block)


def mk_config(initial_stake_distribution: list[Coin]) -> Config:
    initial_inferred_total_stake = sum(c.value for c in initial_stake_distribution)
    return Config.cryptarchia_v0_0_1(initial_inferred_total_stake).replace(
        k=1,
        active_slot_coeff=0.5,
    )


def mk_genesis_state(initial_stake_distribution: list[Coin]) -> LedgerState:
    return LedgerState(
        block=BlockHeader(slot=Slot(0), parent=bytes(32)),
        nonce=bytes(32),
        commitments_spend={c.commitment() for c in initial_stake_distribution},
        commitments_lead={c.commitment() for c in initial_stake_distribution},
        nullifiers=set(),
    )


def mk_block(
    parent: BlockHeader, slot: int, coin: Coin, content=bytes(32), orphaned_proofs=[]
) -> BlockHeader:
    assert type(parent) == BlockHeader, type(parent)
    assert type(slot) == int, type(slot)
    from hashlib import sha256

    return BlockHeader(
        slot=Slot(slot),
        parent=parent.id(),
        content_size=len(content),
        content_id=sha256(content).digest(),
        leader_proof=MockLeaderProof.new(coin, Slot(slot), parent=parent.id()),
        orphaned_proofs=orphaned_proofs,
    )


def mk_chain(
    parent: BlockHeader, coin: Coin, slots: list[int]
) -> tuple[list[BlockHeader], Coin]:
    assert type(parent) == BlockHeader
    chain = []
    for s in slots:
        block = mk_block(parent=parent, slot=s, coin=coin)
        chain.append(block)
        parent = block
        coin = coin.evolve()
    return chain, coin
