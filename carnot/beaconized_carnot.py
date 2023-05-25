from typing import Set

from carnot import Carnot, Block, TimeoutQc, Vote, Event, Send, Quorum
from beacon import *
from overlay import EntropyOverlay

@dataclass
class BeaconizedBlock(Block):
    beacon: RandomBeacon
    # public key of the proposer
    pk: PublicKey


class BeaconizedCarnot(Carnot):
    def __init__(self, sk: PrivateKey, overlay: EntropyOverlay, entropy: bytes = b""):
        self.sk = sk
        self.pk = bytes(self.sk.get_g1())
        self.random_beacon = RandomBeaconHandler(
            RecoveryMode.generate_beacon(entropy, -1)
        )
        overlay.set_entropy(self.random_beacon.last_beacon.entropy())
        super().__init__(self.pk, overlay=overlay)

    def approve_block(self, block: BeaconizedBlock, votes: Set[Vote]) -> Event:
        assert block.id() in self.safe_blocks
        assert len(votes) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_child_committee(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)
        assert self.highest_voted_view < block.view

        if self.overlay.is_member_of_root_committee(self.id):
            qc = self.build_qc(block.view, block, None)
        else:
            qc = None

        vote: Vote = Vote(
            block=block.id(),
            voter=self.id,
            view=block.view,
            qc=qc
        )

        self.highest_voted_view = max(self.highest_voted_view, block.view)

        # root members send votes to next leader, we update our beacon first
        if self.overlay.is_member_of_root_committee(self.id):
            assert(self.random_beacon.verify_happy(block.beacon, block.pk, block.qc.view))
            self.overlay.set_entropy(self.random_beacon.last_beacon.entropy())
            return Send(to=self.overlay.leader(), payload=vote)

        # otherwise we send to the parent committee and update the beacon second
        return_event = Send(to=self.overlay.parent_committee(self.id), payload=vote)
        assert(self.random_beacon.verify_happy(block.beacon, block.pk, block.qc.view))
        self.overlay.set_entropy(self.random_beacon.last_beacon.entropy())
        return return_event

    def receive_timeout_qc(self, timeout_qc: TimeoutQc):
        super().receive_timeout_qc(timeout_qc)
        if timeout_qc.view < self.current_view:
            return
        new_beacon = RecoveryMode.generate_beacon(self.random_beacon.last_beacon.entropy(), timeout_qc.view)
        self.random_beacon.verify_unhappy(new_beacon, timeout_qc.view)
        self.overlay.set_entropy(self.random_beacon.last_beacon.entropy())

    def propose_block(self, view: View, quorum: Quorum) -> Event:
            event: Event = super().propose_block(view, quorum)
            block = event.payload
            beacon = NormalMode.generate_beacon(self.sk, block.qc.view)
            block = BeaconizedBlock(view=block.view, qc=block.qc, _id=block._id, beacon=beacon, pk = G1Element.from_bytes(self.pk))
            event.payload = block
            return event
