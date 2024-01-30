from typing import TypeAlias, List, Optional
from hashlib import sha256, blake2b

# Please note this is still a work in progress
from dataclasses import dataclass

Id: TypeAlias = bytes


@dataclass
class Epoch:
    # identifier of the epoch, counting incrementally from 0
    epoch: int


@dataclass
class TimeConfig:
    # How many slots in a epoch, all epochs will have the same number of slots
    slots_per_epoch: int
    # How long a slot lasts in seconds
    slot_duration: int
    # Start of the first epoch, in unix timestamp second precision
    chain_start_time: int


# An absolute unique indentifier of a slot, counting incrementally from 0
@dataclass
class Slot:
    absolute_slot: int

    def from_unix_timestamp_s(config: TimeConfig, timestamp_s: int) -> "Slot":
        absolute_slot = (timestamp_s - config.chain_start_time) // config.slot_duration
        return Slot(absolute_slot)

    def epoch(self, config: TimeConfig) -> Epoch:
        return self.absolute_slot // config.slots_per_epoch


@dataclass
class Config:
    k: int
    time: TimeConfig


@dataclass
class BlockHeader:
    slot: Slot
    parent: Id
    content_size: int
    content_id: Id

    # **Attention**:
    # The ID of a block header is defined as the 32byte blake2b hash of its fields
    # as serialized in the format specified by the 'HEADER' rule in 'messages.abnf'.
    #
    # The following code is to be considered as a reference implementation, mostly to be used for testing.
    def id(self) -> Id:
        # version byte
        bytes = bytearray(b"\x01")
        # header type
        bytes += b"\x00"
        # content size
        bytes += int.to_bytes(self.content_size, length=4, byteorder="big")
        # content id
        assert len(self.content_id) == 32
        bytes += self.content_id
        # slot
        bytes += int.to_bytes(self.slot.absolute_slot, length=8, byteorder="big")
        # parent
        assert len(self.content_id) == 32
        bytes += self.parent
        return blake2b(bytes, digest_size=32).digest()


@dataclass
class Chain:
    blocks: List[BlockHeader]

    def tip(self) -> BlockHeader:
        return self.blocks[-1]

    def length(self) -> int:
        return len(self.blocks)

    def contains_block(self, block: BlockHeader) -> bool:
        return block in self.blocks

    def block_position(self, block: BlockHeader) -> int:
        assert self.contains_block(block)
        for i, b in enumerate(self.blocks):
            if b == block:
                return i


class Follower:
    def __init__(self, genesis: BlockHeader, config: Config):
        self.config = config
        self.forks = []
        self.local_chain = Chain([genesis])

    # We don't do any validation in the current version
    def validate_header(block: BlockHeader) -> bool:
        return True

    # Try appending this block to an existing chain and return whether
    # the operation was successful
    def try_extend_chains(self, block: BlockHeader) -> bool:
        if self.local_chain.tip().id() == block.parent():
            self.local_chain.blocks.append(block)
            return True

        for chain in self.forks:
            if chain.tip().id() == block.parent():
                chain.blocks.append(block)
                return True

        return False

    def try_create_fork(self, block: BlockHeader) -> Optional[Chain]:
        chains = self.forks + [self.local_chain]
        for chain in chains:
            if self.chain.contains_block(block):
                block_position = chain.block_position(block)
                return Chain(blocks=chain.blocks[:block_position] + [block])

        return None

    def on_block(self, block: BlockHeader):
        if not self.validate_header(block):
            return

        # check if the new block extends an existing chain
        if self.try_extend_chains(block):
            return

        # if we get here, we might need to create a fork
        new_chain = self.try_create_fork(block)
        if new_chain is not None:
            self.forks.append(new_chain)
        # otherwise, we're missing the parent block
        # in that case, just ignore the block

    # Evaluate the fork choice rule and return the block header of the block that should be the head of the chain
    def fork_choice(local_chain: Chain, forks: List[Chain]) -> Chain:
        # TODO: define k and s
        return maxvalid_bg(local_chain, forks, 0, 0)

    def tip(self) -> BlockHeader:
        return self.fork_choice()


@dataclass
class Coin:
    pk: int
    value: int


@dataclass
class LedgerState:
    """
    A snapshot of the ledger state up to some height
    """

    block: Id = None
    nonce: bytes = None
    total_stake: int = None


@dataclass
class EpochState:
    # for details of snapshot schedule please see:
    # https://github.com/IntersectMBO/ouroboros-consensus/blob/fe245ac1d8dbfb563ede2fdb6585055e12ce9738/docs/website/contents/for-developers/Glossary.md#epoch-structure

    # The stake distribution snapshot is taken at the beginning of the previous epoch
    stake_distribution_snapshot: LedgerState

    # The nonce snapshot is taken 7k/f slots into the previous epoch
    nonce_snapshot: LedgerState

    def total_stake(self) -> int:
        """Returns the total stake that will be used to reletivize leadership proofs during this epoch"""
        return self.stake_distribution_snapshot.total_stake

    def nonce(self) -> bytes:
        return self.nonce_snapshot.nonce


@dataclass
class LeaderConfig:
    active_slot_coeff: float = 0.05  # 'f', the rate of occupied slots


def phi(f: float, alpha: float) -> float:
    """
    params:
      f: 'active slot coefficient' - the rate of occupied slots
      alpha: relative stake held by the validator

    returns: the probability that this validator should win the slot lottery
    """
    return 1 - (1 - f) ** alpha


class MOCK_LEADER_VRF:
    """NOT SECURE: A mock VRF function where the sk and pk are assummed to be the same"""

    ORDER = 2**256

    @classmethod
    def vrf(cls, sk: int, nonce: bytes, slot: int) -> int:
        h = sha256()
        h.update(int.to_bytes(sk, length=32))
        h.update(nonce)
        h.update(int.to_bytes(slot, length=16))  # 64bit slots
        return int.from_bytes(h.digest())

    @classmethod
    def verify(cls, r, pk, nonce, slot):
        raise NotImplemented()


@dataclass
class Leader:
    config: LeaderConfig
    coin: Coin

    def is_slot_leader(self, epoch: EpochState, slot: Slot) -> bool:
        f = self.config.active_slot_coeff
        relative_stake = self.coin.value / epoch.total_stake()

        r = MOCK_LEADER_VRF.vrf(self.coin.pk, epoch.nonce(), slot)

        return r < MOCK_LEADER_VRF.ORDER * phi(f, relative_stake)

    def propose_block(self, slot: Slot, parent: BlockHeader) -> BlockHeader:
        return BlockHeader(parent=parent.id(), slot=slot)


def common_prefix_len(a: Chain, b: Chain) -> int:
    for i, (x, y) in enumerate(zip(a.blocks, b.blocks)):
        if x.id() != y.id():
            return i
    return min(len(a.blocks), len(b.blocks))


def chain_density(chain: Chain, slot: Slot) -> int:
    return len(
        [
            block
            for block in chain.blocks
            if block.slot.absolute_slot < slot.absolute_slot
        ]
    )


# Implementation of the fork choice rule as defined in the Ouroboros Genesis paper
# k defines the forking depth of chain we accept without more analysis
# s defines the length of time (unit of slots) after the fork happened we will inspect for chain density
def maxvalid_bg(local_chain: Chain, forks: List[Chain], k: int, s: int) -> Chain:
    cmax = local_chain
    for chain in forks:
        lowest_common_ancestor = common_prefix_len(cmax, chain)
        m = cmax.length() - lowest_common_ancestor
        if m <= k:
            # Classic longest chain rule with parameter k
            if cmax.length() < chain.length():
                cmax = chain
        else:
            # The chain is forking too much, we need to pay a bit more attention
            # In particular, select the chain that is the densest after the fork
            forking_slot = Slot(
                cmax.blocks[lowest_common_ancestor].slot.absolute_slot + s
            )
            cmax_density = chain_density(cmax, forking_slot)
            candidate_density = chain_density(chain, forking_slot)
            if cmax_density < candidate_density:
                cmax = chain

    return cmax


if __name__ == "__main__":
    pass
