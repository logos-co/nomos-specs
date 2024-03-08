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
    return Config(
        k=1,
        active_slot_coeff=1,
        epoch_stake_distribution_stabilization=3,
        epoch_period_nonce_buffer=3,
        epoch_period_nonce_stabilization=4,
        time=TimeConfig(slot_duration=1, chain_start_time=0),
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


def mk_chain(
    base_state: LedgerState, length: int, coin: Coin
) -> tuple[list[BlockHeader], Coin]:
    chain = []
    parent = base_state.block
    for i in range(length):
        chain.append(
            mk_block(
                parent=parent,
                slot=base_state.slot.absolute_slot + i,
                coin=coin,
            )
        )
        coin = coin.evolve()
    return chain, coin
