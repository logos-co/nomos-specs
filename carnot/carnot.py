from dataclasses import dataclass
from typing import TypeAlias, List, Set, Self, Optional, Dict
from abc import abstractmethod

Id: TypeAlias = bytes
View: TypeAlias = int
Committee: TypeAlias = Set[Id]


def int_to_id(i: int) -> Id:
    return bytes(str(i), encoding="utf8")


@dataclass(unsafe_hash=True)
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
        return int_to_id(hash((self.view, self.qc.view, self.qc.block)))


@dataclass(unsafe_hash=True)
class Vote:
    block: Id
    view: View
    voter: Id
    qc: Optional[Qc]


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
        """
        :param _id:
        :return: true if the participant with Id _id is member of the root committee withing the tree overlay
        """
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
    def parent_committee(self, _id: Id) -> Optional[Committee]:
        """
        :param _id:
        :return: Some(parent committee) of the participant with Id _id withing the committee tree overlay
        or Empty if the member with Id _id is a participant of the root committee
        """
        pass

    @abstractmethod
    def super_majority_threshold(self, _id: Id) -> int:
        """
        Amount of distinct number of messages for a node with Id _id member of a committee
        The return value may change depending on which committee the node is member of, including the leader
        :return:
        """
        if self.is_leader(_id):
            pass
        elif self.member_of_root_committee(_id):
            pass
        else:
            pass


def download(view) -> Block:
    raise NotImplementedError


class Carnot:
    def __init__(self, _id: Id):
        self.id: Id = _id
        self.current_view: View = 0
        self.highest_voted_view: View = 0
        self.local_high_qc: Optional[Qc] = None
        self.latest_committed_view: View = 0
        self.safe_blocks: Dict[Id, Block] = dict()
        self.last_timeout_view_qc: Optional[TimeoutQc] = None
        self.last_timeout_view: Optional[View] = None
        self.overlay: Overlay = Overlay()  # TODO: integrate overlay
        self.committed_blocks: Dict[Id, Block] = dict()

    def block_is_safe(self, block: Block) -> bool:
        match block.qc:
            case StandardQc() as standard:
                if standard.view < self.latest_committed_view:
                    return False
                return block.view >= self.latest_committed_view and block.view == (standard.view + 1)
            case AggregateQc() as aggregated:
                if aggregated.high_qc().view < self.latest_committed_view:
                    return False
                return block.view >= self.current_view and block.view == (aggregated.view + 1)

    def update_high_qc(self, qc: Qc):
        match (self.local_high_qc, qc):
            case (None, StandardQc() as new_qc):
                self.local_high_qc = new_qc
            case (None, AggregateQc() as new_qc):
                self.local_high_qc = new_qc.high_qc()
            case (old_qc, StandardQc() as new_qc) if new_qc.view > old_qc.view:
                self.local_high_qc = new_qc
            case (old_qc, AggregateQc() as new_qc) if new_qc.high_qc().view != old_qc.view:
                self.local_high_qc = new_qc.high_qc()

    def receive_block(self, block: Block):
        assert block.parent() in self.safe_blocks
        if block.id() in self.safe_blocks or block.view <= self.latest_committed_view:
            return

        if self.block_is_safe(block):
            self.safe_blocks[block.id()] = block
            self.update_high_qc(block.qc)
            self.try_commit_grand_parent(block)

    def vote(self, block: Block, votes: Set[Vote]):
        assert block.id() in self.safe_blocks
        assert len(votes) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.child_committee(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)
        assert block.view > self.highest_voted_view

        if self.overlay.member_of_root_com(self.id):
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=self.current_view,
                qc=self.build_qc(votes)
            )
            self.send(vote, self.overlay.leader(self.current_view + 1))
        else:
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=self.current_view,
                qc=None
            )
        self.send(vote, *self.overlay.parent_committee(self.id))
        self.increment_voted_view(block.view)  # to avoid voting again for this view.
        self.increment_view_qc(block.qc)

    def forward_vote(self, vote: Vote):
        assert vote.block in self.safe_blocks
        assert self.overlay.child_committee(self.id, vote.voter)

        if self.overlay.member_of_root_com(self.id):
            self.send(vote, self.overlay.leader(self.current_view + 1))

    def build_qc(self, quorum: Quorum) -> Qc:
        pass

    def propose_block(self, view: View, quorum: Quorum):
        assert self.overlay.is_leader(self.id)
        assert len(quorum) == self.overlay.super_majority_threshold(self.id)

        qc = self.build_qc(quorum)
        block = Block(view=view, qc=qc)
        self.broadcast(block)

    def local_timeout(self, new_overlay: Overlay):
        self.last_timeout_view = self.current_view
        self.increment_voted_view(self.current_view)
        self.overlay = new_overlay
        if self.overlay.member_of_leaf_committee(self.id):
            raise NotImplementedError()

    def timeout(self, view: View, msgs: Set["TimeoutMsg"]):
        raise NotImplementedError()

    def send(self, vote: Vote, *ids: Id):
        pass

    def broadcast(self, block):
        pass

    def try_commit_grand_parent(self, block: Block):
        parent = self.safe_blocks.get(block.parent())
        grand_parent = self.safe_blocks.get(parent.parent())
        # this case should just trigger on genesis_case,
        # as the preconditions on outer calls should check on block validity
        if not parent or not grand_parent:
            return
        can_commit = (
                parent.view == (grand_parent.view + 1) and
                isinstance(block.qc, (StandardQc, )) and
                isinstance(parent.qc, (StandardQc, ))
        )
        if can_commit:
            self.committed_blocks[grand_parent.id()] = grand_parent

    def increment_voted_view(self, view: View):
        self.highest_voted_view = max(view, self.highest_voted_view)

    def increment_view_qc(self, qc: Qc) -> bool:
        if qc.view < self.current_view:
            return False
        self.last_timeout_view_qc = None
        self.current_view = qc.view + 1
        return True


if __name__ == "__main__":
    pass
