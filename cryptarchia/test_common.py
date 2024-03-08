from .cryptarchia import (
    Config,
    TimeConfig,
    Id,
    Slot,
    Coin,
    BlockHeader,
    LedgerState,
    MockLeaderProof,
)


def mk_config() -> Config:
    return Config.cryptarchia_v0_0_1().replace(
        k=1,
        active_slot_coeff=1.0,
    )


def mk_genesis_state(initial_stake_distribution: list[Coin]) -> LedgerState:
    return LedgerState(
        block=bytes(32),
        nonce=bytes(32),
        total_stake=sum(c.value for c in initial_stake_distribution),
        commitments_spend={c.commitment() for c in initial_stake_distribution},
        commitments_lead={c.commitment() for c in initial_stake_distribution},
        nullifiers=set(),
    )


def mk_block(
    parent: Id, slot: int, coin: Coin, content=bytes(32), orphaned_proofs=[]
) -> BlockHeader:
    assert len(parent) == 32
    from hashlib import sha256

    return BlockHeader(
        slot=Slot(slot),
        parent=parent,
        content_size=len(content),
        content_id=sha256(content).digest(),
        leader_proof=MockLeaderProof.new(coin, Slot(slot), parent=parent),
        orphaned_proofs=orphaned_proofs,
    )


def mk_chain(parent, coin: Coin, slots: list[int]) -> tuple[list[BlockHeader], Coin]:
    chain = []
    for s in slots:
        block = mk_block(parent=parent, slot=s, coin=coin)
        chain.append(block)
        parent = block.id()
        coin = coin.evolve()
    return chain, coin
