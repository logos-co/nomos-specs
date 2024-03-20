from typing import TypeAlias, List, Optional
from hashlib import sha256, blake2b
from math import floor
from copy import deepcopy
from itertools import chain
import functools
from dataclasses import dataclass, field, replace

import numpy as np

Id: TypeAlias = bytes


@dataclass(frozen=True)
class Epoch:
    # identifier of the epoch, counting incrementally from 0
    epoch: int

    def prev(self) -> "Epoch":
        return Epoch(self.epoch - 1)


@dataclass
class TimeConfig:
    # How long a slot lasts in seconds
    slot_duration: int
    # Start of the first epoch, in unix timestamp second precision
    chain_start_time: int


@dataclass
class Config:
    k: int  # The depth of a block before it is considered immutable.
    active_slot_coeff: float  # 'f', the rate of occupied slots

    # The stake distribution is always taken at the beginning of the previous epoch.
    # This parameters controls how many slots to wait for it to be stabilized
    # The value is computed as epoch_stake_distribution_stabilization * int(floor(k / f))
    epoch_stake_distribution_stabilization: int
    # This parameter controls how many slots we wait after the stake distribution
    # snapshot has stabilized to take the nonce snapshot.
    epoch_period_nonce_buffer: int
    # This parameter controls how many slots we wait for the nonce snapshot to be considered
    # stabilized
    epoch_period_nonce_stabilization: int

    # -- Stake Relativization Params
    initial_inferred_total_stake: int  # D_0
    total_stake_learning_rate: int  # beta

    time: TimeConfig

    @staticmethod
    def cryptarchia_v0_0_1(initial_inferred_total_stake) -> "Config":
        return Config(
            k=2160,
            active_slot_coeff=0.05,
            epoch_stake_distribution_stabilization=3,
            epoch_period_nonce_buffer=3,
            epoch_period_nonce_stabilization=4,
            initial_inferred_total_stake=initial_inferred_total_stake,
            total_stake_learning_rate=0.8,
            time=TimeConfig(
                slot_duration=1,
                chain_start_time=0,
            ),
        )

    @property
    def base_period_length(self) -> int:
        return int(floor(self.k / self.active_slot_coeff))

    @property
    def epoch_relative_nonce_slot(self) -> int:
        return (
            self.epoch_stake_distribution_stabilization + self.epoch_period_nonce_buffer
        ) * self.base_period_length

    @property
    def epoch_length(self) -> int:
        return (
            self.epoch_relative_nonce_slot
            + self.epoch_period_nonce_stabilization * self.base_period_length
        )

    @property
    def s(self):
        """
        The Security Paramater. This paramter controls how many slots one must wait before we
        have high confidence that k blocks have been produced.
        """
        return self.base_period_length * 3

    def replace(self, **kwarg) -> "Config":
        return replace(self, **kwarg)


# An absolute unique indentifier of a slot, counting incrementally from 0
@dataclass
@functools.total_ordering
class Slot:
    absolute_slot: int

    def from_unix_timestamp_s(config: TimeConfig, timestamp_s: int) -> "Slot":
        absolute_slot = (timestamp_s - config.chain_start_time) // config.slot_duration
        return Slot(absolute_slot)

    def epoch(self, config: Config) -> Epoch:
        return Epoch(self.absolute_slot // config.epoch_length)

    def encode(self) -> bytes:
        return int.to_bytes(self.absolute_slot, length=8, byteorder="big")

    def __eq__(self, other):
        return self.absolute_slot == other.absolute_slot

    def __lt__(self, other):
        return self.absolute_slot < other.absolute_slot

    def __str__(self):
        return f"Slot({self.absolute_slot})"


@dataclass
class Coin:
    sk: int
    value: int
    nonce: bytes = bytes(32)

    @property
    def pk(self) -> int:
        return self.sk

    def encode_sk(self) -> bytes:
        return int.to_bytes(self.sk, length=32, byteorder="big")

    def encode_pk(self) -> bytes:
        return int.to_bytes(self.pk, length=32, byteorder="big")

    def evolve(self) -> "Coin":
        h = blake2b(digest_size=32)
        h.update(b"coin-evolve")
        h.update(self.encode_sk())
        h.update(self.nonce)
        evolved_nonce = h.digest()

        return Coin(nonce=evolved_nonce, sk=self.sk, value=self.value)

    def commitment(self) -> Id:
        # TODO: mocked until CL is understood
        value_bytes = int.to_bytes(self.value, length=32, byteorder="big")

        h = sha256()
        h.update(b"coin-commitment")
        h.update(self.nonce)
        h.update(self.encode_pk())
        h.update(value_bytes)
        return h.digest()

    def nullifier(self) -> Id:
        # TODO: mocked until CL is understood
        value_bytes = int.to_bytes(self.value, length=32, byteorder="big")

        h = sha256()
        h.update(b"coin-nullifier")
        h.update(self.nonce)
        h.update(self.encode_pk())
        h.update(value_bytes)
        return h.digest()


@dataclass
class MockLeaderProof:
    commitment: Id
    nullifier: Id
    evolved_commitment: Id
    slot: Slot
    parent: Id

    @staticmethod
    def new(coin: Coin, slot: Slot, parent: Id):
        evolved_coin = coin.evolve()

        return MockLeaderProof(
            commitment=coin.commitment(),
            nullifier=coin.nullifier(),
            evolved_commitment=evolved_coin.commitment(),
            slot=slot,
            parent=parent,
        )

    def verify(self, slot: Slot, parent: Id):
        # TODO: verification not implemented
        return slot == self.slot and parent == self.parent


@dataclass
class BlockHeader:
    slot: Slot
    parent: Id
    content_size: int
    content_id: Id
    leader_proof: MockLeaderProof
    orphaned_proofs: List["BlockHeader"] = field(default_factory=list)

    def update_header_hash(self, h):
        # version byte
        h.update(b"\x01")

        # content size
        h.update(int.to_bytes(self.content_size, length=4, byteorder="big"))

        # content id
        assert len(self.content_id) == 32
        h.update(self.content_id)

        # slot
        h.update(self.slot.encode())

        # parent
        assert len(self.parent) == 32
        h.update(self.parent)

        # leader proof
        assert len(self.leader_proof.commitment) == 32
        h.update(self.leader_proof.commitment)
        assert len(self.leader_proof.nullifier) == 32
        h.update(self.leader_proof.nullifier)
        assert len(self.leader_proof.evolved_commitment) == 32
        h.update(self.leader_proof.evolved_commitment)

        # orphaned proofs
        h.update(int.to_bytes(len(self.orphaned_proofs), length=4, byteorder="big"))
        for proof in self.orphaned_proofs:
            proof.update_header_hash(h)

    # **Attention**:
    # The ID of a block header is defined as the 32byte blake2b hash of its fields
    # as serialized in the format specified by the 'HEADER' rule in 'messages.abnf'.
    #
    # The following code is to be considered as a reference implementation, mostly to be used for testing.
    def id(self) -> Id:
        h = blake2b(digest_size=32)
        self.update_header_hash(h)
        return h.digest()


@dataclass
class Chain:
    blocks: List[BlockHeader]
    genesis: Id

    def tip_id(self) -> Id:
        if len(self.blocks) == 0:
            return self.genesis
        return self.tip().id()

    def tip(self) -> BlockHeader:
        return self.blocks[-1]

    def length(self) -> int:
        return len(self.blocks)

    def contains_block(self, block: Id) -> bool:
        return any(block == b.id() for b in self.blocks)

    def block_position(self, block: Id) -> int:
        assert self.contains_block(block)
        for i, b in enumerate(self.blocks):
            if b.id() == block:
                return i


@dataclass
class LedgerState:
    """
    A snapshot of the ledger state up to some block
    """

    block: Id = None
    slot: Slot = field(default_factory=lambda: Slot(0))

    # This nonce is used to derive the seed for the slot leader lottery
    # It's updated at every block by hashing the previous nonce with the nullifier
    # Note that this does not prevent nonce grinding at the last slot before the nonce snapshot
    nonce: Id = None

    # set of commitments
    commitments_spend: set[Id] = field(default_factory=set)

    # set of commitments eligible to lead
    commitments_lead: set[Id] = field(default_factory=set)

    # set of nullified coins
    nullifiers: set[Id] = field(default_factory=set)

    # -- Stake Relativization State
    # The number of observed leaders (block proposers + orphans), this is used to infer total stake
    leader_count: int = 0

    def copy(self):
        return LedgerState(
            block=self.block,
            slot=self.slot,
            nonce=self.nonce,
            commitments_spend=deepcopy(self.commitments_spend),
            commitments_lead=deepcopy(self.commitments_lead),
            nullifiers=deepcopy(self.nullifiers),
            leader_count=self.leader_count,
        )

    def replace(self, **kwarg) -> "LedgerState":
        return replace(self, **kwarg)

    def verify_eligible_to_spend(self, commitment: Id) -> bool:
        return commitment in self.commitments_spend

    def verify_eligible_to_lead(self, commitment: Id) -> bool:
        return commitment in self.commitments_lead

    def verify_unspent(self, nullifier: Id) -> bool:
        return nullifier not in self.nullifiers

    def apply(self, block: BlockHeader):
        assert block.parent == self.block

        h = blake2b(digest_size=32)
        h.update("epoch-nonce".encode(encoding="utf-8"))
        h.update(self.nonce)
        h.update(block.leader_proof.nullifier)
        h.update(block.slot.encode())

        self.nonce = h.digest()
        self.block = block.id()
        self.slot = block.slot
        for proof in chain(block.orphaned_proofs, [block]):
            proof = proof.leader_proof
            self.nullifiers.add(proof.nullifier)
            self.commitments_spend.add(proof.evolved_commitment)
            self.commitments_lead.add(proof.evolved_commitment)
            self.leader_count += 1


@dataclass
class EpochState:
    # for details of snapshot schedule please see:
    # https://github.com/IntersectMBO/ouroboros-consensus/blob/fe245ac1d8dbfb563ede2fdb6585055e12ce9738/docs/website/contents/for-developers/Glossary.md#epoch-structure

    # The stake distribution snapshot is taken at the beginning of the previous epoch
    stake_distribution_snapshot: LedgerState

    # The nonce snapshot is taken 7k/f slots into the previous epoch
    nonce_snapshot: LedgerState

    # Total stake is inferred from watching the block production rate over the past epoch.
    # This inferred total stake is used to relativize stake values in the leadership lottery.
    inferred_total_stake: int

    def verify_eligible_to_lead_due_to_age(self, commitment: Id) -> bool:
        # A coin is eligible to lead if it was committed to before the the stake
        # distribution snapshot was taken or it was produced by a leader proof since the snapshot was taken.
        #
        # This verification is checking that first condition.
        #
        # NOTE: `ledger_state.commitments_spend` is a super-set of `ledger_state.commitments_lead`

        return self.stake_distribution_snapshot.verify_eligible_to_spend(commitment)

    def total_stake(self) -> int:
        """Returns the total stake that will be used to reletivize leadership proofs during this epoch"""
        return self.inferred_total_stake

    def nonce(self) -> bytes:
        return self.nonce_snapshot.nonce


class Follower:
    def __init__(self, genesis_state: LedgerState, config: Config):
        self.config = config
        self.forks = []
        self.local_chain = Chain([], genesis=genesis_state.block)
        self.genesis_state = genesis_state
        self.ledger_state = {genesis_state.block: genesis_state.copy()}
        self.epoch_state = {
            (Epoch(0), genesis_state.block): EpochState(
                stake_distribution_snapshot=genesis_state,
                nonce_snapshot=genesis_state,
                inferred_total_stake=config.initial_inferred_total_stake,
            )
        }

    def validate_header(self, block: BlockHeader, chain: Chain) -> bool:
        # TODO: verify blocks are not in the 'future'
        current_state = self.ledger_state[chain.tip_id()].copy()
        orphaned_commitments = set()
        # first, we verify adopted leadership transactions
        for proof in block.orphaned_proofs:
            proof = proof.leader_proof
            # each proof is validated against the last state of the ledger of the chain this block
            # is being added to before that proof slot
            parent_state = self.state_at_slot_beginning(chain, proof.slot).copy()
            # we add effects of previous orphaned proofs to the ledger state
            parent_state.commitments_lead |= orphaned_commitments
            epoch_state = self.compute_epoch_state(proof.slot.epoch(self.config), chain)
            if self.verify_slot_leader(
                proof.slot, proof, epoch_state, parent_state, current_state
            ):
                # if an adopted leadership proof is valid we need to apply its effects to the ledger state
                orphaned_commitments.add(proof.evolved_commitment)
                current_state.nullifiers.add(proof.nullifier)
            else:
                print("WARN: orphan proof is invalid")
                # otherwise, the whole block is invalid
                return False

        parent_state = self.ledger_state[block.parent].copy()
        parent_state.commitments_lead |= orphaned_commitments
        epoch_state = self.compute_epoch_state(block.slot.epoch(self.config), chain)
        # TODO: this is not the full block validation spec, only slot leader is verified
        return self.verify_slot_leader(
            block.slot, block.leader_proof, epoch_state, parent_state, current_state
        )

    def verify_slot_leader(
        self,
        slot: Slot,
        proof: MockLeaderProof,
        # coins are old enough if their commitment is in the stake distribution snapshot
        epoch_state: EpochState,
        # commitments derived from leadership coin evolution are checked in the parent state
        parent_state: LedgerState,
        # nullifiers are checked in the current state
        current_state: LedgerState,
    ) -> bool:
        return (
            proof.verify(slot, parent_state.block)  # verify slot leader proof
            and (
                parent_state.verify_eligible_to_lead(proof.commitment)
                or epoch_state.verify_eligible_to_lead_due_to_age(proof.commitment)
            )
            and current_state.verify_unspent(proof.nullifier)
        )

    # Try appending this block to an existing chain and return whether
    # the operation was successful
    def try_extend_chains(self, block: BlockHeader) -> Optional[Chain]:
        if self.tip_id() == block.parent:
            return self.local_chain

        for chain in self.forks:
            if chain.tip_id() == block.parent:
                return chain

        return None

    def try_create_fork(self, block: BlockHeader) -> Optional[Chain]:
        if self.genesis_state.block == block.parent:
            # this block is forking off the genesis state
            return Chain(blocks=[], genesis=self.genesis_state.block)

        chains = self.forks + [self.local_chain]
        for chain in chains:
            if chain.contains_block(block.parent):
                block_position = chain.block_position(block.parent)
                return Chain(
                    blocks=chain.blocks[: block_position + 1],
                    genesis=self.genesis_state.block,
                )

        return None

    def on_block(self, block: BlockHeader):
        # check if the new block extends an existing chain
        new_chain = self.try_extend_chains(block)
        if new_chain is None:
            # we failed to extend one of the existing chains,
            # therefore we might need to create a new fork
            new_chain = self.try_create_fork(block)
            if new_chain is not None:
                self.forks.append(new_chain)
            else:
                print("WARN: missing parent block")
                # otherwise, we're missing the parent block
                # in that case, just ignore the block
                return

        if not self.validate_header(block, new_chain):
            print("WARN: invalid header")
            return

        new_chain.blocks.append(block)

        # We may need to switch forks, lets run the fork choice rule to check.
        new_chain = self.fork_choice()
        self.local_chain = new_chain

        new_state = self.ledger_state[block.parent].copy()
        new_state.apply(block)
        self.ledger_state[block.id()] = new_state

    def unimported_orphans(self, parent: Id) -> list[BlockHeader]:
        """
        Returns all unimported orphans w.r.t. the given parent state.
        Orphans are returned in the order that they should be imported.
        """
        tip_state = self.ledger_state[parent]

        orphans = []
        for fork in [self.local_chain, *self.forks]:
            for block in fork.blocks:
                for b in [*block.orphaned_proofs, block]:
                    if b.leader_proof.nullifier not in tip_state.nullifiers:
                        orphans += [b]

        return orphans

    # Evaluate the fork choice rule and return the block header of the block that should be the head of the chain
    def fork_choice(self) -> Chain:
        return maxvalid_bg(
            self.local_chain, self.forks, k=self.config.k, s=self.config.s
        )

    def tip(self) -> BlockHeader:
        return self.local_chain.tip()

    def tip_id(self) -> Id:
        return self.local_chain.tip_id()

    def tip_state(self) -> LedgerState:
        return self.ledger_state[self.tip_id()]

    def state_at_slot_beginning(self, chain: Chain, slot: Slot) -> LedgerState:
        for block in reversed(chain.blocks):
            if block.slot < slot:
                return self.ledger_state[block.id()]

        return self.genesis_state

    def epoch_start_slot(self, epoch) -> Slot:
        return Slot(epoch.epoch * self.config.epoch_length)

    def stake_distribution_snapshot(self, epoch, chain):
        # stake distribution snapshot happens at the beginning of the previous epoch,
        # i.e. for epoch e, the snapshot is taken at the last block of epoch e-2
        slot = Slot(epoch.prev().epoch * self.config.epoch_length)
        return self.state_at_slot_beginning(chain, slot)

    def nonce_snapshot(self, epoch, chain):
        # nonce snapshot happens partway through the previous epoch after the
        # stake distribution has stabilized
        slot = Slot(
            self.config.epoch_relative_nonce_slot
            + self.epoch_start_slot(epoch.prev()).absolute_slot
        )
        return self.state_at_slot_beginning(chain, slot)

    def compute_epoch_state(self, epoch: Epoch, chain: Chain) -> EpochState:
        if epoch.epoch == 0:
            return EpochState(
                stake_distribution_snapshot=self.genesis_state,
                nonce_snapshot=self.genesis_state,
                inferred_total_stake=self.config.initial_inferred_total_stake,
            )

        stake_distribution_snapshot = self.stake_distribution_snapshot(epoch, chain)
        nonce_snapshot = self.nonce_snapshot(epoch, chain)

        memo_block_id = nonce_snapshot.block
        if state := self.epoch_state.get((epoch, memo_block_id)):
            return state

        prev_epoch = self.compute_epoch_state(epoch.prev(), chain)

        # Compute inferred total stake from results of last epoch
        block_proposals_last_epoch = (
            nonce_snapshot.leader_count - stake_distribution_snapshot.leader_count
        )
        expected_blocks_per_slot = np.log(1 / (1 - self.config.active_slot_coeff))
        h = (
            self.config.total_stake_learning_rate
            * prev_epoch.inferred_total_stake
            / expected_blocks_per_slot
        )
        T = self.config.epoch_relative_nonce_slot
        mean_blocks_per_slot = block_proposals_last_epoch / T
        blocks_per_slot_err = expected_blocks_per_slot - mean_blocks_per_slot
        inferred_total_stake = prev_epoch.inferred_total_stake - h * blocks_per_slot_err

        state = EpochState(
            stake_distribution_snapshot=stake_distribution_snapshot,
            nonce_snapshot=nonce_snapshot,
            inferred_total_stake=inferred_total_stake,
        )

        self.epoch_state[(epoch, memo_block_id)] = state
        return state

    def _infer_total_stake(
        self, last_inferred_total_stake, block_proposals, slots
    ) -> int:
        last_nonce_snapshot = self.state_at_slot_beginning(
            chain, Slot(nonce_snapshot.slot.absolute_slot - self.config.epoch_length)
        )

        prev_epoch_total_stake = self.compute_epoch_state(
            last_nonce_snapshot.slot, chain
        ).inferred_total_stake

        # Compute inferred total stake from results of last epoch
        block_proposals_last_epoch = (
            nonce_snapshot.leader_count - last_nonce_snapshot.leader_count
        )
        expected_blocks_per_slot = np.log(1 / (1 - self.config.active_slot_coeff))
        h = (
            self.config.total_stake_learning_rate
            * prev_epoch_total_stake
            / expected_blocks_per_slot
        )
        # T is epoch length in all epochs except for the first epoch.
        epoch_length = (
            nonce_snapshot.slot.absolute_slot - last_nonce_snapshot.slot.absolute_slot
        )
        mean_blocks_per_slot = block_proposals_last_epoch / T
        blocks_per_slot_err = expected_blocks_per_slot - mean_blocks_per_slot
        inferred_total_stake = int(prev_epoch_total_stake - h * blocks_per_slot_err)
        return inferred_total_stake


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
    def vrf(cls, coin: Coin, epoch_nonce: bytes, slot: Slot) -> int:
        h = sha256()
        h.update(b"lead")
        h.update(epoch_nonce)
        h.update(slot.encode())
        h.update(coin.encode_sk())
        h.update(coin.nonce)

        return int.from_bytes(h.digest())

    @classmethod
    def verify(cls, r, pk, nonce, slot):
        raise NotImplemented()


@dataclass
class Leader:
    config: Config
    coin: Coin

    def try_prove_slot_leader(
        self, epoch: EpochState, slot: Slot, parent: Id
    ) -> MockLeaderProof | None:
        if self._is_slot_leader(epoch, slot):
            return MockLeaderProof.new(self.coin, slot, parent)

    def _is_slot_leader(self, epoch: EpochState, slot: Slot):
        relative_stake = self.coin.value / epoch.total_stake()

        r = MOCK_LEADER_VRF.vrf(self.coin, epoch.nonce(), slot)

        return r < MOCK_LEADER_VRF.ORDER * phi(
            self.config.active_slot_coeff, relative_stake
        )


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
