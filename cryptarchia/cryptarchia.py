import functools
from itertools import islice
import logging
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field, replace
from hashlib import blake2b, sha256
from math import floor
from typing import Dict, Generator, List, TypeAlias
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)


class Hash(bytes):
    ORDER = 2**256

    def __new__(cls, dst, *data):
        assert isinstance(dst, bytes)
        h = sha256()
        h.update(dst)
        for d in data:
            h.update(d)
        return super().__new__(cls, h.digest())

    def __deepcopy__(self, memo):
        return self


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

    # The stake distribution is taken at the beginning of the previous epoch.
    # This parameters controls how many slots to wait for it to be stabilized
    # The value is computed as
    #     epoch_stake_distribution_stabilization * int(floor(k / f))
    epoch_stake_distribution_stabilization: int
    # This parameter controls how many `base periods` we wait after stake
    # distribution snapshot has stabilized to take the nonce snapshot.
    epoch_period_nonce_buffer: int
    # This parameter controls how many `base periods` we wait for the nonce
    # snapshot to be considered stabilized
    epoch_period_nonce_stabilization: int

    # -- Stake Relativization Params
    initial_total_active_stake: int  # D_0
    total_active_stake_learning_rate: int  # beta

    time: TimeConfig

    @staticmethod
    def cryptarchia_v0_0_1(initial_total_active_stake) -> "Config":
        return Config(
            k=2160,
            active_slot_coeff=0.05,
            epoch_stake_distribution_stabilization=3,
            epoch_period_nonce_buffer=3,
            epoch_period_nonce_stabilization=4,
            initial_total_active_stake=initial_total_active_stake,
            total_active_stake_learning_rate=0.8,
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
        The Security Paramater. This paramter controls how many slots one must
        wait before we have high confidence that k blocks have been produced.
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

    def __hash__(self):
        return hash(self.absolute_slot)


@dataclass
class Note:
    value: int
    sk: int  # TODO: rename to nf_sk
    nonce: Hash = Hash(b"nonce")
    unit: Hash = Hash(b"NMO")
    state: Hash = Hash(b"state")
    zone_id: Hash = Hash(b"ZoneID")

    def __post_init__(self):
        assert 0 <= self.value <= 2**64

    @property
    def pk(self) -> int:
        return self.sk

    def encode_sk(self) -> bytes:
        return int.to_bytes(self.sk, length=32, byteorder="big")

    def encode_pk(self) -> bytes:
        return int.to_bytes(self.pk, length=32, byteorder="big")

    def commitment(self) -> Hash:
        value_bytes = int.to_bytes(self.value, length=32, byteorder="big")
        return Hash(
            b"NOMOS_NOTE_CM",
            self.state,
            value_bytes,
            self.unit,
            self.nonce,
            self.encode_pk(),
            self.zone_id,
        )

    def nullifier(self) -> Hash:
        return Hash(b"NOMOS_NOTE_NF", self.commitment(), self.encode_sk())


@dataclass
class MockLeaderProof:
    note: Note
    slot: Slot
    parent: Hash

    def epoch_nonce_contribution(self) -> Hash:
        return Hash(
            b"NOMOS_NONCE_CONTRIB",
            self.slot.encode(),
            self.note.commitment(),
            self.note.encode_sk(),
        )

    def verify(
        self, slot: Slot, parent: Hash, commitments: set[Hash], nullifiers: set[Hash]
    ):
        # TODO: verify slot lottery
        return (
            slot == self.slot
            and parent == self.parent
            and self.note.commitment() in commitments
            and self.note.nullifier() not in nullifiers
        )


@dataclass
class BlockHeader:
    slot: Slot
    parent: Hash
    content_size: int
    content_id: Hash
    leader_proof: MockLeaderProof

    # **Attention**:
    # The ID of a block header is defined as the hash of its fields
    # as serialized in the format specified by the 'HEADER' rule in 'messages.abnf'.
    #
    # The following code is to be considered as a reference implementation, mostly to be used for testing.
    def id(self) -> Hash:
        return Hash(
            b"BLOCK_ID",
            b"\x01",  # version
            int.to_bytes(self.content_size, length=4, byteorder="big"),  # content size
            self.content_id,  # content id
            self.slot.encode(),  # slot
            self.parent,  # parent
            # leader proof
            self.leader_proof.epoch_nonce_contribution(),
            # self.leader_proof -- the proof itself needs to be include in the hash
        )

    def __hash__(self):
        return hash(self.id())


@dataclass
class LedgerState:
    """
    A snapshot of the ledger state up to some block
    """

    block: BlockHeader

    # This nonce is used to derive the seed for the slot leader lottery.
    # It's updated at every block by hashing the previous nonce with the
    # leader proof's nonce contribution
    nonce: Hash = None

    # set of note commitments
    commitments: set[Hash] = field(default_factory=set)

    # set of nullified notes
    nullifiers: set[Hash] = field(default_factory=set)

    # -- Stake Relativization State
    # The number of observed leaders, this measurement is
    # used in inferring total active stake in the network.
    leader_count: int = 0

    def copy(self):
        return LedgerState(
            block=self.block,
            nonce=self.nonce,
            commitments=deepcopy(self.commitments),
            nullifiers=deepcopy(self.nullifiers),
            leader_count=self.leader_count,
        )

    def replace(self, **kwarg) -> "LedgerState":
        return replace(self, **kwarg)

    def apply(self, block: BlockHeader):
        assert block.parent == self.block.id()

        self.nonce = Hash(
            b"EPOCH_NONCE",
            self.nonce,
            block.leader_proof.epoch_nonce_contribution(),
            block.slot.encode(),
        )
        self.leader_count += 1
        self.block = block


@dataclass
class EpochState:
    # for details of snapshot schedule please see:
    # https://github.com/IntersectMBO/ouroboros-consensus/blob/fe245ac1d8dbfb563ede2fdb6585055e12ce9738/docs/website/contents/for-developers/Glossary.md#epoch-structure

    # Stake distribution snapshot is taken at the start of the previous epoch
    stake_distribution_snapshot: LedgerState

    # Nonce snapshot is taken 6k/f slots into the previous epoch
    nonce_snapshot: LedgerState

    # Total stake is inferred from watching block production rate over the past
    # epoch. This inferred total stake is used to relativize stake values in the
    # leadership lottery.
    inferred_total_active_stake: int

    def total_active_stake(self) -> int:
        """
        Returns the inferred total stake participating in consensus.
        Total active stake is used to reletivize a note's value in leadership proofs.
        """
        return self.inferred_total_active_stake

    def nonce(self) -> bytes:
        return self.nonce_snapshot.nonce

class State(Enum):
    ONLINE = 1
    BOOTSTRAPPING = 2

class Follower:
    def __init__(self, genesis_state: LedgerState, config: Config):
        self.config = config
        self.forks: list[Hash] = []
        self.local_chain = genesis_state.block.id()
        self.genesis_state = genesis_state
        self.ledger_state = {genesis_state.block.id(): genesis_state.copy()}
        self.epoch_state = {}
        self.state = State.BOOTSTRAPPING
        self.lib = genesis_state.block.id()  # Last immutable block, initially the genesis block

    def to_online(self):
        """
        Call this method when the follower has finished bootstrapping. While this is somewhat left to implementations
        https://www.notion.so/Cryptarchia-v1-Bootstrapping-Synchronization-1fd261aa09df81ac94b5fb6a4eff32a6 contains a great deal
        of information and is the reference for the Rust implementation.
        """
        if self.state != State.BOOTSTRAPPING:
            raise RuntimeError("Follower is not in BOOTSTRAPPING state")
        self.state = State.ONLINE
        self.update_lib()

    def validate_header(self, block: BlockHeader):
        # TODO: verify blocks are not in the 'future'
        if block.parent not in self.ledger_state:
            raise ParentNotFound

        if not is_ancestor(self.lib, block.parent, self.ledger_state):
            # If the block is not an ancestor of the last immutable block, we cannot process it.
            raise ImmutableFork

        current_state = self.ledger_state[block.parent].copy()

        epoch_state = self.compute_epoch_state(
            block.slot.epoch(self.config), block.parent
        )

        # TODO: this is not the full block validation spec, only slot leader is verified
        if not block.leader_proof.verify(
            block.slot,
            block.parent,
            epoch_state.stake_distribution_snapshot.commitments,
            current_state.nullifiers,
        ):
            raise InvalidLeaderProof

    def on_block(self, block: BlockHeader):
        if block.id() in self.ledger_state:
            logger.warning("dropping already processed block")
            return

        self.validate_header(block)

        new_state = self.ledger_state[block.parent].copy()
        new_state.apply(block)
        self.ledger_state[block.id()] = new_state

        if block.parent == self.local_chain:
            # simply extending the local chain
            self.local_chain = block.id()
        else:
            # otherwise, this block creates a fork
            self.forks.append(block.id())

            # remove any existing fork that is superceded by this block
            if block.parent in self.forks:
                self.forks.remove(block.parent)

            # We may need to switch forks, lets run the fork choice rule to check.
            new_tip = self.fork_choice()
            self.forks.append(self.local_chain)
            self.forks.remove(new_tip)
            self.local_chain = new_tip

        if self.state == State.ONLINE:
            self.update_lib()


    # Update the lib, and prune forks that do not descend from it.
    def update_lib(self):
        """
        Computes the last immutable block, which is the k-th block in the chain.
        The last immutable block is the block that is guaranteed to be part of the chain
        and will not be reverted.
        """
        if self.state != State.ONLINE:
            return
        # prune forks that do not descend from the last immutable block, this is needed to avoid Genesis rule to roll back
        # past the LIB
        self.lib = next(islice(iter_chain(self.local_chain, self.ledger_state), self.config.k, None), self.local_chain).block.id()
        self.forks = [
            f for f in self.forks if is_ancestor(self.lib, f, self.ledger_state)
        ]


    # Evaluate the fork choice rule and return the chain we should be following
    def fork_choice(self) -> Hash:
        if self.state == State.BOOTSTRAPPING:
            return maxvalid_bg(
                self.local_chain,
                self.forks,
                k=self.config.k,
                s=self.config.s,
                states=self.ledger_state,
            )
        elif self.state == State.ONLINE:
            return maxvalid_mc(
                self.local_chain,
                self.forks,
                k=self.config.k,
                states=self.ledger_state,
            )
        else:
            raise RuntimeError(f"Unknown follower state: {self.state}")

    def tip(self) -> BlockHeader:
        return self.tip_state().block

    def tip_id(self) -> Hash:
        return self.local_chain

    def tip_state(self) -> LedgerState:
        return self.ledger_state[self.tip_id()]

    def state_at_slot_beginning(self, tip: Hash, slot: Slot) -> LedgerState:
        for state in iter_chain(tip, self.ledger_state):
            if state.block.slot < slot:
                return state
        return self.genesis_state

    def epoch_start_slot(self, epoch) -> Slot:
        return Slot(epoch.epoch * self.config.epoch_length)

    def stake_distribution_snapshot(self, epoch, tip: Hash):
        # stake distribution snapshot happens at the beginning of the previous epoch,
        # i.e. for epoch e, the snapshot is taken at the last block of epoch e-2
        slot = Slot(epoch.prev().epoch * self.config.epoch_length)
        return self.state_at_slot_beginning(tip, slot)

    def nonce_snapshot(self, epoch, tip):
        # nonce snapshot happens partway through the previous epoch after the
        # stake distribution has stabilized
        slot = Slot(
            self.config.epoch_relative_nonce_slot
            + self.epoch_start_slot(epoch.prev()).absolute_slot
        )
        return self.state_at_slot_beginning(tip, slot)

    def compute_epoch_state(self, epoch: Epoch, tip: Hash) -> EpochState:
        if epoch.epoch == 0:
            return EpochState(
                stake_distribution_snapshot=self.genesis_state,
                nonce_snapshot=self.genesis_state,
                inferred_total_active_stake=self.config.initial_total_active_stake,
            )

        stake_distribution_snapshot = self.stake_distribution_snapshot(epoch, tip)
        nonce_snapshot = self.nonce_snapshot(epoch, tip)

        # we memoize epoch states to avoid recursion killing our performance
        memo_block_id = nonce_snapshot.block.id()
        if state := self.epoch_state.get((epoch, memo_block_id)):
            return state

        # To update our inference of total stake, we need the prior estimate which
        # was calculated last epoch. Thus we recurse here to retreive the previous
        # estimate of total stake.
        prev_epoch = self.compute_epoch_state(epoch.prev(), tip)
        inferred_total_active_stake = self._infer_total_active_stake(
            prev_epoch, nonce_snapshot, stake_distribution_snapshot
        )

        state = EpochState(
            stake_distribution_snapshot=stake_distribution_snapshot,
            nonce_snapshot=nonce_snapshot,
            inferred_total_active_stake=inferred_total_active_stake,
        )

        self.epoch_state[(epoch, memo_block_id)] = state
        return state

    def _infer_total_active_stake(
        self,
        prev_epoch: EpochState,
        nonce_snapshot: LedgerState,
        stake_distribution_snapshot: LedgerState,
    ):
        # Infer total stake from empirical block production rate in last epoch

        # Since we need a stable inference of total stake for the start of this epoch,
        # we limit our look back period to the start of last epoch until when the nonce
        # snapshot was taken.
        block_proposals_last_epoch = (
            nonce_snapshot.leader_count - stake_distribution_snapshot.leader_count
        )
        T = self.config.epoch_relative_nonce_slot
        mean_blocks_per_slot = block_proposals_last_epoch / T
        expected_blocks_per_slot = np.log(1 / (1 - self.config.active_slot_coeff))
        blocks_per_slot_err = expected_blocks_per_slot - mean_blocks_per_slot
        h = (
            self.config.total_active_stake_learning_rate
            * prev_epoch.inferred_total_active_stake
            / expected_blocks_per_slot
        )
        return int(prev_epoch.inferred_total_active_stake - h * blocks_per_slot_err)

    def blocks_by_slot(self, from_slot: Slot) -> Generator[BlockHeader, None, None]:
        # Returns blocks in the given range of slots in order of slot
        # NOTE: In real implementation, this should be done by optimized data structures.
        blocks_by_slot: dict[Slot, list[BlockHeader]] = defaultdict(list)
        for state in self.ledger_state.values():
            if from_slot <= state.block.slot:
                blocks_by_slot[state.block.slot].append(state.block)
        for slot in sorted(blocks_by_slot.keys()):
            for block in blocks_by_slot[slot]:
                yield block


def phi(f: float, alpha: float) -> float:
    """
    params:
      f: 'active slot coefficient' - the rate of occupied slots
      alpha: relative stake held by the validator

    returns: the probability that this validator should win the slot lottery
    """
    return 1 - (1 - f) ** alpha


@dataclass
class Leader:
    config: Config
    note: Note

    def try_prove_slot_leader(
        self, epoch: EpochState, slot: Slot, parent: Hash
    ) -> MockLeaderProof | None:
        if self._is_slot_leader(epoch, slot):
            return MockLeaderProof(self.note, slot, parent)

    def _is_slot_leader(self, epoch: EpochState, slot: Slot):
        relative_stake = self.note.value / epoch.total_active_stake()

        ticket = Hash(
            b"LEAD",
            epoch.nonce(),
            slot.encode(),
            self.note.commitment(),
            self.note.encode_sk(),
        )
        ticket = int.from_bytes(ticket)

        return ticket < Hash.ORDER * phi(self.config.active_slot_coeff, relative_stake)


def iter_chain(
    tip: Hash, states: Dict[Hash, LedgerState]
) -> Generator[LedgerState, None, None]:
    while tip in states:
        yield states[tip]
        tip = states[tip].block.parent


def iter_chain_blocks(
    tip: Hash, states: Dict[Hash, LedgerState]
) -> Generator[BlockHeader, None, None]:
    for state in iter_chain(tip, states):
        yield state.block

def is_ancestor(a: Hash, b: Hash, states: Dict[Hash, LedgerState]) -> bool:
    """
    Returns True if `a` is an ancestor of `b` in the chain.
    """
    for state in iter_chain(b, states):
        if state.block.id() == a:
            return True
    return False

def common_prefix_depth(
    a: Hash, b: Hash, states: Dict[Hash, LedgerState]
) -> tuple[int, list[BlockHeader], int, list[BlockHeader]]:
    a_blocks = iter_chain_blocks(a, states)
    b_blocks = iter_chain_blocks(b, states)

    seen = {}
    a_suffix: list[BlockHeader] = []
    b_suffix: list[BlockHeader] = []
    depth = 0
    while True:
        try:
            a_block = next(a_blocks)
            a_suffix.append(a_block)
            a_block_id = a_block.id()
            if a_block_id in seen:
                # we had seen this block from the fork chain
                return (
                    depth,
                    list(reversed(a_suffix[: depth + 1])),
                    seen[a_block_id],
                    list(reversed(b_suffix[: seen[a_block_id] + 1])),
                )

            seen[a_block_id] = depth
        except StopIteration:
            pass

        try:
            b_block = next(b_blocks)
            b_suffix.append(b_block)
            b_block_id = b_block.id()
            if b_block_id in seen:
                # we had seen the fork in the local chain
                return (
                    seen[b_block_id],
                    list(reversed(a_suffix[: seen[b_block_id] + 1])),
                    depth,
                    list(reversed(b_suffix[: depth + 1])),
                )
            seen[b_block_id] = depth
        except StopIteration:
            pass

        depth += 1

    assert False


def chain_density(chain: list[BlockHeader], slot: Slot) -> int:
    return sum(1 for b in chain if b.slot < slot)


def block_children(states: Dict[Hash, LedgerState]) -> Dict[Hash, set[Hash]]:
    children = defaultdict(set)
    for c, state in states.items():
        children[state.block.parent].add(c)

    return children


# Implementation of the Ouroboros Genesis fork choice rule.
# The fork choice has two phases:
# 1. if the chain is not forking too deeply, we apply the longest chain fork choice rule
# 2. otherwise we look at the chain density immidiately following the fork
#
# k defines the forking depth of a chain at which point we switch phases.
# s defines the length of time (unit of slots) after the fork happened we will inspect for chain density
def maxvalid_bg(
    local_chain: Hash,
    forks: List[Hash],
    k: int,
    s: int,
    states: Dict[Hash, LedgerState],
) -> Hash:
    assert type(local_chain) == Hash, type(local_chain)
    assert all(type(f) == Hash for f in forks)

    cmax = local_chain
    for fork in forks:
        cmax_depth, cmax_suffix, fork_depth, fork_suffix = common_prefix_depth(
            cmax, fork, states
        )
        if cmax_depth <= k:
            # Longest chain fork choice rule
            if cmax_depth < fork_depth:
                cmax = fork
        else:
            # The chain is forking too much, we need to pay a bit more attention
            # In particular, select the chain that is the densest after the fork
            cmax_divergent_block = cmax_suffix[0]

            forking_slot = Slot(cmax_divergent_block.slot.absolute_slot + s)
            cmax_density = chain_density(cmax_suffix, forking_slot)
            fork_density = chain_density(fork_suffix, forking_slot)

            if cmax_density < fork_density:
                cmax = fork

    return cmax


# Implementation of the Ouroboros Praos fork choice rule.
# The fork choice has two phases:
# 1. if the chain is not forking too deeply, we apply the longest chain fork choice rule
# 2. otherwise we discard the fork
#
# k defines the forking depth of a chain at which point we switch phases.
def maxvalid_mc(
    local_chain: Hash,
    forks: List[Hash],
    k: int,
    states: Dict[Hash, LedgerState],
) -> Hash:
    assert type(local_chain) == Hash, type(local_chain)
    assert all(type(f) == Hash for f in forks)

    cmax = local_chain
    for fork in forks:
        cmax_depth, _, fork_depth, _ = common_prefix_depth(
            cmax, fork, states
        )
        if cmax_depth <= k:
            # Longest chain fork choice rule
            if cmax_depth < fork_depth:
                cmax = fork

    return cmax

class ParentNotFound(Exception):
    def __str__(self):
        return "Parent not found"


class InvalidLeaderProof(Exception):
    def __str__(self):
        return "Invalid leader proof"

class ImmutableFork(Exception):
    def __str__(self):
        return "Block is forking from the last immutable block"


if __name__ == "__main__":
    pass
