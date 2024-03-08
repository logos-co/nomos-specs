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
