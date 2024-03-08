from .cryptarchia import Config, TimeConfig


def mk_config() -> Config:
    return Config(
        k=1,
        active_slot_coeff=1,
        epoch_stake_distribution_stabilization=3,
        epoch_period_nonce_buffer=3,
        epoch_period_nonce_stabilization=4,
        time=TimeConfig(slot_duration=1, chain_start_time=0),
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
