from typing import TypeAlias, List, Optional, Dict
from hashlib import sha256, blake2b
from math import floor
from copy import deepcopy
import itertools
import functools
from dataclasses import dataclass, field, replace
import logging

import numpy as np


logger = logging.getLogger(__name__)


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
    commitment: Id = bytes(32)
    nullifier: Id = bytes(32)
    evolved_commitment: Id = bytes(32)
    slot: Slot = field(default_factory=lambda: Slot(0))
    parent: Id = bytes(32)

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
        if slot != self.slot:
            logger.warning("PoL: wrong slot")
            return False
        if parent != self.parent:
            logger.warning("PoL: wrong parent")
            return False
        return True


@dataclass
class BlockHeader:
    slot: Slot
    parent: Id = bytes(32)
    content_size: int = 0
    content_id: Id = bytes(32)
    leader_proof: MockLeaderProof = field(default_factory=MockLeaderProof)

    orphaned_proofs: List["BlockHeader"] = field(default_factory=list)

    def __post_init__(self):
        assert type(self.slot) == Slot
        assert type(self.parent) == Id
        assert self.slot == self.leader_proof.slot
        assert self.parent == self.leader_proof.parent

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
class LedgerState:
    """
    A snapshot of the ledger state up to some block
    """

    block: BlockHeader

    # This nonce is used to derive the seed for the slot leader lottery.
    # It's updated at every block by hashing the previous nonce with the
    # leader proof's nullifier.
    #
    # NOTE that this does not prevent nonce grinding at the last slot
    # when the nonce snapshot is taken
    nonce: Id = None

    # set of commitments
    commitments_spend: set[Id] = field(default_factory=set)

    # set of commitments eligible to lead
    commitments_lead: set[Id] = field(default_factory=set)

    # set of nullified coins
    nullifiers: set[Id] = field(default_factory=set)

    # -- Stake Relativization State
    # The number of observed leaders (blocks + orphans), this measurement is
    # used in inferring total active stake in the network.
    leader_count: int = 0
    height: int = 0

    def copy(self):
        return LedgerState(
            block=self.block,
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
        assert block.parent == self.block.id()

        h = blake2b(digest_size=32)
        h.update("epoch-nonce".encode(encoding="utf-8"))
        h.update(self.nonce)
        h.update(block.leader_proof.nullifier)
        h.update(block.slot.encode())

        self.nonce = h.digest()
        self.block = block
        for proof in itertools.chain(block.orphaned_proofs, [block]):
            self.apply_leader_proof(proof.leader_proof)

        self.height += 1

    def apply_leader_proof(self, proof: MockLeaderProof):
        self.nullifiers.add(proof.nullifier)
        self.commitments_spend.add(proof.evolved_commitment)
        self.commitments_lead.add(proof.evolved_commitment)
        self.leader_count += 1


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

    def verify_eligible_to_lead_due_to_age(self, commitment: Id) -> bool:
        # A coin is eligible to lead if it was committed to before the the stake
        # distribution snapshot was taken or it was produced by a leader proof
        # since the snapshot was taken.
        #
        # This verification is checking that first condition.
        #
        # NOTE: `ledger_state.commitments_spend` is a super-set of `ledger_state.commitments_lead`
        return self.stake_distribution_snapshot.verify_eligible_to_spend(commitment)

    def total_active_stake(self) -> int:
        """
        Returns the inferred total stake participating in consensus.
        Total active stake is used to reletivize a coin's value in leadership proofs.
        """
        return self.inferred_total_active_stake

    def nonce(self) -> bytes:
        return self.nonce_snapshot.nonce


class Follower:
    def __init__(self, genesis_state: LedgerState, config: Config):
        self.config = config
        self.forks = []
        self.local_chain = genesis_state.block.id()
        self.genesis_state = genesis_state
        self.ledger_state = {genesis_state.block.id(): genesis_state.copy()}
        self.epoch_state = {}

    def validate_header(self, block: BlockHeader) -> bool:
        # TODO: verify blocks are not in the 'future'
        if block.parent not in self.ledger_state:
            logger.warning("We have not seen block parent")
            return False

        current_state = self.ledger_state[block.parent].copy()

        # we use the proposed block epoch state to validate orphans as well
        epoch_state = self.compute_epoch_state(
            block.slot.epoch(self.config), block.parent
        )

        # first, we verify adopted leadership transactions
        for orphan in block.orphaned_proofs:
            # orphan proofs are checked in two ways
            # 1. ensure they are valid locally in their original branch
            # 2. ensure it does not conflict with current state

            # We take a shortcut for (1.) by restricting orphans to proofs we've
            # already processed in other branches.
            if orphan.id() not in self.ledger_state:
                logger.warning("missing orphan proof")
                return False

            # (2.) is satisfied by verifying the proof against current state ensuring:
            # - it is a valid proof
            # - and the nullifier has not already been spent
            if not self.verify_slot_leader(
                orphan.slot,
                orphan.parent,
                orphan.leader_proof,
                epoch_state,
                current_state,
            ):
                logger.warning("invalid orphan proof")
                return False

            # if an adopted leadership proof is valid we need to apply its
            # effects to the ledger state
            current_state.apply_leader_proof(orphan.leader_proof)

        # TODO: this is not the full block validation spec, only slot leader is verified
        return self.verify_slot_leader(
            block.slot,
            block.parent,
            block.leader_proof,
            epoch_state,
            current_state,
        )

    def verify_slot_leader(
        self,
        slot: Slot,
        parent: Id,
        proof: MockLeaderProof,
        # coins are old enough if their commitment is in the stake distribution snapshot
        epoch_state: EpochState,
        # nullifiers (and commitments) are checked against the current state.
        # For now, we assume proof parent state and current state are identical.
        # This will change once we start putting merkle roots in headers
        current_state: LedgerState,
    ) -> bool:
        if not proof.verify(slot, parent):
            logger.warning("invalid PoL")
            return False
        if not (
            current_state.verify_eligible_to_lead(proof.commitment)
            or epoch_state.verify_eligible_to_lead_due_to_age(proof.commitment)
        ):
            logger.warning("invalid commitment")
            return False

        if not current_state.verify_unspent(proof.nullifier):
            logger.warning("PoL coin already spent")
            return False

        return True

    def on_block(self, block: BlockHeader):
        if not self.validate_header(block):
            logger.warning("invalid header")
            return

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

    def unimported_orphans(self) -> list[BlockHeader]:
        """
        Returns all unimported orphans w.r.t. the given tip's state.
        Orphans are returned in the order that they should be imported.
        """
        tip_state = self.tip_state().copy()

        orphans = []

        for fork in self.forks:
            _, fork_depth = common_prefix_depth(
                tip_state.block.id(), fork, self.ledger_state
            )
            fork_chain = chain_suffix(fork, fork_depth, self.ledger_state)
            for block_state in fork_chain:
                b = block_state.block
                if b.leader_proof.nullifier not in tip_state.nullifiers:
                    tip_state.nullifiers.add(b.leader_proof.nullifier)
                    orphans += [b]

        return orphans

    # Evaluate the fork choice rule and return the chain we should be following
    def fork_choice(self) -> Id:
        return maxvalid_bg(
            self.local_chain,
            self.forks,
            self.ledger_state,
            k=self.config.k,
            s=self.config.s,
        )

    def tip(self) -> BlockHeader:
        return self.tip_state().block

    def tip_id(self) -> Id:
        return self.local_chain

    def tip_state(self) -> LedgerState:
        return self.ledger_state[self.tip_id()]

    def state_at_slot_beginning(self, tip: Id, slot: Slot) -> LedgerState:
        for state in iter_chain(tip, self.ledger_state):
            if state.block.slot < slot:
                return state
        return self.genesis_state

    def epoch_start_slot(self, epoch) -> Slot:
        return Slot(epoch.epoch * self.config.epoch_length)

    def stake_distribution_snapshot(self, epoch, tip: Id):
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

    def compute_epoch_state(self, epoch: Epoch, tip: Id) -> EpochState:
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


def phi(f: float, alpha: float) -> float:
    """
    params:
      f: 'active slot coefficient' - the rate of occupied slots
      alpha: relative stake held by the validator

    returns: the probability that this validator should win the slot lottery
    """
    return 1 - (1 - f) ** alpha


class MOCK_LEADER_VRF:
    """NOT SECURE: A mock VRF function"""

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
        relative_stake = self.coin.value / epoch.total_active_stake()

        r = MOCK_LEADER_VRF.vrf(self.coin, epoch.nonce(), slot)

        return r < MOCK_LEADER_VRF.ORDER * phi(
            self.config.active_slot_coeff, relative_stake
        )


def iter_chain(tip: Id, states: Dict[Id, LedgerState]):
    while tip in states:
        yield states[tip]
        tip = states[tip].block.parent


def chain_suffix(tip: Id, n: int, states: Dict[Id, LedgerState]) -> list[LedgerState]:
    return reversed(list(itertools.islice(iter_chain(tip, states), n)))


def common_prefix_depth(a: Id, b: Id, states: Dict[Id, LedgerState]) -> (int, int):
    a_blocks = iter_chain(a, states)
    b_blocks = iter_chain(b, states)

    seen = {}
    depth = 0
    while True:
        try:
            a_block = next(a_blocks).block.id()
            if a_block in seen:
                # we had seen this block from the fork chain
                return depth, seen[a_block]

            seen[a_block] = depth
        except StopIteration:
            pass

        try:
            b_block = next(b_blocks).block.id()
            if b_block in seen:
                # we had seen the fork in the local chain
                return seen[b_block], depth
            seen[b_block] = depth
        except StopIteration:
            pass

        depth += 1

    assert False


def chain_density(
    head: Id, slot: Slot, reorg_depth: int, states: Dict[Id, LedgerState]
) -> int:
    assert type(head) == Id
    density = 0
    block = head
    for _ in range(reorg_depth):
        if states[block].block.slot.absolute_slot < slot.absolute_slot:
            density += 1
        block = states[block].block.parent

    return density


# Implementation of the fork choice rule as defined in the Ouroboros Genesis paper
# k defines the forking depth of chain we accept without more analysis
# s defines the length of time (unit of slots) after the fork happened we will inspect for chain density
def maxvalid_bg(
    local_chain: Id,
    forks: List[Id],
    states: Dict[Id, LedgerState],
    k: int,
    s: int,
) -> Id:
    assert type(local_chain) == Id
    assert all(type(f) == Id for f in forks)

    cmax = local_chain
    for fork in forks:
        local_depth, fork_depth = common_prefix_depth(cmax, fork, states)
        if local_depth <= k:
            # Classic longest chain rule with parameter k
            if local_depth < fork_depth:
                cmax = fork
        else:
            # The chain is forking too much, we need to pay a bit more attention
            # In particular, select the chain that is the densest after the fork
            forking_block = local_chain
            for _ in range(local_depth):
                forking_block = states[forking_block].block.parent

            forking_slot = Slot(states[forking_block].block.slot.absolute_slot + s)
            cmax_density = chain_density(cmax, forking_slot, local_depth, states)
            candidate_density = chain_density(fork, forking_slot, fork_depth, states)

            if cmax_density < candidate_density:
                cmax = fork

    return cmax


if __name__ == "__main__":
    pass
