from dataclasses import dataclass
from typing import TypeAlias, List, Set, Self
from rusty_results import Option, Some, Empty, Result, Ok, Err
from abc import abstractmethod
from pprint import pformat

Id: TypeAlias = bytes
View: TypeAlias = int
Committee: TypeAlias = Set[Id]


@dataclass
class StandardQc:
    block: Id
    view: View

    def view(self) -> View:
        return self.view


@dataclass
class AggregateQc:
    qcs: List[StandardQc]
    view: View

    def view(self) -> View:
        return self.view

    def high_qc(self) -> StandardQc:
        return max(self.qcs, key=lambda qc: qc.view)


Qc: TypeAlias = StandardQc | AggregateQc

@dataclass
class Block:
    view: View
    qc: Qc

    def extends(self, ancestor: Self) -> bool:
        """
        :param ancestor:
        :return: true if block is descendant of the ancestor in the chain
        """
        return self.view > ancestor.view

    def parent(self) -> Id:
        return self.qc.block

    def id(self) -> Id:
        return int.to_bytes(hash(self), length=32, byteorder="little")


@dataclass
class Vote:
    block: Id
    view: View
    voter: Id
    qc: Option[Qc]


@dataclass
class TimeoutQc:
    view: View
    high_qc: AggregateQc


Quorum: TypeAlias = Set[Vote] | Set[TimeoutQc]


class Overlay:
    """
    Overlay structure for a View
    """
    @abstractmethod
    def is_leader(self, _id: Id):
        """
        :param _id:  Node id to be checked
        :return: true if node is the leader of the current view
        """
        pass

    def leader(self, view: View) -> Id:
        """
        :param view:
        :return: the leader Id of the specified view
        """
        pass

    @abstractmethod
    def member_of_leaf_committee(self, _id: Id) -> bool:
        """
        :param _id: Node id to be checked
        :return: true if the participant with Id _id is in the leaf committee of the committee overlay
        """
        pass

    @abstractmethod
    def member_of_root_committee(self, _id: Id) -> bool:
        pass

    @abstractmethod
    def member_of_root_com(self, _id: Id) -> bool:
        """
        :param _id:
        :return: true if the participant with Id _id is member of the root committee withing the tree overlay
        """
        pass

    @abstractmethod
    def member_of_internal_com(self, _id: Id) -> bool:
        """
        :param _id:
        :return:  truee if the participant with Id _id is member of internal committees within the committee tree overlay
        """
        pass

    @abstractmethod
    def child_committee(self, parent: Id, child: Id) -> bool:
        """
        :param parent:
        :param child:
        :return: true if participant with Id child is member of the child committee of the participant with Id parent
        """
        pass

    @abstractmethod
    def parent_committee(self, _id: Id) -> Option[Committee]:
        """
        :param _id:
        :return: Some(parent committee) of the participant with Id _id withing the committee tree overlay
        or Empty if the member with Id _id is a participant of the root committee
        """
        pass


def download(view) -> Block:
    raise NotImplementedError


def supermajority(votes: Set[Vote]) -> bool:
    raise NotImplementedError


def leader_supermajorty(votes: Set[Vote]) -> bool:
    raise NotImplementedError


def more_than_supermajority(votes: Set[Vote]) -> bool:
    raise NotImplementedError


class Carnot:
    def __init__(self, _id: Id):
        self.id: Id = _id
        self.current_view: View = 0
        self.local_high_qc: Option[Qc] = Empty()
        self.latest_committed_view: View = 0
        self.safe_blocks: Set[Id] = set()
        self.last_timeout_view_qc: Option[TimeoutQc] = Empty()
        self.last_timeout_view: Option[View] = Empty()
        self.overlay: Overlay = Overlay()  # TODO: integrate overlay

    def block_is_safe(self, block: Block) -> bool:
        match block.qc:
            case StandardQc() as standard:
                if standard.view <=self.latest_committed_view:
                    return False
                return block.view >= self.latest_committed_view and block.view == (standard.view + 1)
            case AggregateQc() as aggregated:
                if aggregated.high_qc().view <= self.latest_committed_view:
                    return False
                return block.view >= self.current_view

    def update_high_qc(self, qc: Qc):
        match (self.local_high_qc, qc):
            case (Empty(), StandardQc() as new_qc):
                self.local_high_qc = Some(new_qc)
            case (Empty(), AggregateQc() as new_qc):
                self.local_high_qc = Some(new_qc.high_qc())
            case (Some(old_qc), StandardQc() as new_qc) if new_qc.view > old_qc.view:
                self.local_high_qc = Some(new_qc)
            case (Some(old_qc), AggregateQc() as new_qc) if new_qc.high_qc().view != old_qc.view:
                self.local_high_qc = Some(new_qc.high_qc())

    def receive_block(self, block: Block):
        assert block.parent() in self.safe_blocks
        assert block.id() in self.safe_blocks or block.view <= self.latest_committed_view

        if self.block_is_safe(block):
            self.safe_blocks.add(block.id())
            self.update_high_qc(block.qc)

    def vote(self, block: Block, votes: Set[Vote]):
        assert block.id() in self.safe_blocks
        assert supermajority(votes)
        assert all(self.overlay.child_committee(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)

        if self.overlay.member_of_root_com(self.id):
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=self.current_view,
                qc=Some(self.build_qc(votes))
            )
            self.send(vote, self.overlay.leader(self.current_view + 1))
        else:
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=self.current_view,
                qc=Empty()
            )
        self.send(vote, *self.overlay.parent_committee(self.id))

    def forward_vote(self, vote: Vote):
        assert vote.block in self.safe_blocks
        assert self.overlay.child_committee(self.id, vote.voter)

        if self.overlay.member_of_root_com(self.id):
            self.send(vote, self.overlay.leader(self.current_view + 1))

    def build_qc(self, quorum: Quorum) -> Qc:
        pass

    def propose_block(self, view: View, quorum: Quorum):
        assert self.overlay.is_leader(self.id)
        assert leader_supermajorty(quorum)

        qc = self.build_qc(quorum)
        block = Block(view=view, qc=qc)
        self.broadcast(block)

    def local_timeout(self, new_overlay: Overlay):
        self.last_timeout_view = self.current_view
        self.overlay = new_overlay
        if self.overlay.member_of_leaf_committee(self.id):
            raise NotImplementedError()

    def timeout(self, view: View, msgs: Set["TimeoutMsg"]):
        raise NotImplementedError()

    def send(self, vote: Vote, *ids: Id):
        pass

    def broadcast(self, block):
        pass


if __name__ == "__main__":
    pass
