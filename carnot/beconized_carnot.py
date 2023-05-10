from typing import Set

from carnot import Carnot, Block, TimeoutQc, Vote, Event, Send, Quorum
from beacon import *


class BeaconizedBlock(Block):
    beacon: RandomBeacon


class BeaconizedCarnot(Carnot):
    def __int__(self):
        self.sk = generate_random_sk()
        self.pk = bytes(self.sk.get_gq())
        self.random_beacon = RandomBeaconHandler(
            RandomBeacon(
                version=0,
                context=-1,
                entropy=NormalMode.generate_beacon(self.sk, -1),
                proof=self.pk
            )
        )
        super(Carnot, self).__init__(self.pk)

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
            self.random_beacon.verify_happy(block.beacon)
            return Send(to=self.overlay.leader(), payload=vote)

        # otherwise we send to the parent committee and update the beacon second
        return_event = Send(to=self.overlay.parent_committee(self.id), payload=vote)
        self.random_beacon.verify_happy(block.beacon)
        return return_event

    def receive_timeout_qc(self, timeout_qc: TimeoutQc):
        super(Carnot, self).receive_timeout_qc(timeout_qc)
        if timeout_qc.view < self.current_view:
            return
        entropy = RecoveryMode.generate_beacon(self.random_beacon.last_beacon.entropy, timeout_qc.view)
        new_beacon = RandomBeacon(
            version=0,
            context=self.current_view,
            entropy=entropy,
            proof=b""
        )
        self.random_beacon.verify_unhappy(new_beacon)

    def propose_block(self, view: View, quorum: Quorum) -> Event:
        beacon = RandomBeacon(
            version=0,
            context=self.current_view,
            entropy=NormalMode.generate_beacon(self.sk, self.current_view),
            proof=self.pk
        )
        event: Event = super(Carnot, self).propose_block(view, quorum)
        block = event.payload
        block = BeaconizedBlock(view=block.view, qc=block.qc, _id=block._id, beacon=beacon)
        event.payload = block
        return event
