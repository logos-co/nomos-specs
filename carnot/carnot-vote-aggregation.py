from dataclasses import dataclass
from typing import Union, List, Set, Optional, Type, TypeAlias, Dict
from abc import ABC, abstractmethod

Id = bytes
View = int
Committee = Set[Id]


def int_to_id(i: int) -> Id:
    return bytes(str(i), encoding="utf8")


@dataclass(unsafe_hash=True)
class StandardQc:
    block: Id
    view_num: View  # Changed the variable name to avoid conflict with the class name
    root_qc: bool  # Determines if the QC is build by the leader and is collection of 2/3+1 votes.

    # If it is false then the QC is built by the committees with 2/3 collection of votes from subtree of the collector
    # committee.

    def view(self) -> View:
        return self.view_num  # Changed the method name to view_num


@dataclass
class AggregateQc:
    qcs: List[View]
    highest_qc: StandardQc
    view_num: View  # Changed the variable name to avoid conflict with the class name

    def view(self) -> View:
        return self.view_num  # Changed the method name to view_num

    def high_qc(self) -> StandardQc:
        assert self.highest_qc.view() == max(self.qcs)  # Corrected method call
        assert self.highest_qc.root_qc, "Expected self.highest_qc.root_qc to be True"
        return self.highest_qc


Qc = Union[StandardQc, AggregateQc]  # Changed the type alias to use Union


@dataclass
class Block:
    view_num: View  # Changed the variable name to avoid conflict with the class name
    qc: Qc
    _id: Id

    def extends(self, ancestor):
        if self == ancestor:
            return True
        elif self.parent is None:
            return False
        elif self.parent.view < ancestor.view:  # Check the view of the parent
            return False
        else:
            return self.parent.extends(ancestor)

    def parent(self) -> Id:
        if isinstance(self.qc, StandardQc):
            return self.qc.block
        elif isinstance(self.qc, AggregateQc):
            return self.qc.high_qc().block

    def id(self) -> Id:
        return self._id


@dataclass(unsafe_hash=True)
class Vote:
    block: Id
    view: View
    voter: Id
    qc: Optional[Qc]


@dataclass
class TimeoutQc:
    view: View
    high_qc: Qc
    qc_views: List[View]
    sender_ids: Set[Id]
    sender: Id


class Timeout:
    view: View
    high_qc: Qc
    sender: Id
    timeout_qc: Type[TimeoutQc]


@dataclass
class NewView:
    view: View
    high_qc: Qc
    sender: Id
    timeout_qc: Type[TimeoutQc]


Quorum: TypeAlias = Union[Set[Vote], Set[NewView]]

Payload: TypeAlias = Union[Block, Vote, Timeout, NewView, TimeoutQc]


@dataclass
class BroadCast:
    payload: Payload


@dataclass
class Send:
    to: [Id]
    payload: Payload


Event: TypeAlias = BroadCast | Send


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
        return _id == self.leader()

    @abstractmethod
    def leader(self) -> Id:
        """
        :param view:
        :return: the leader Id of the specified view
        """
        pass

    @abstractmethod
    def next_leader(self) -> Id:
        pass

    @abstractmethod
    def is_member_of_leaf_committee(self, _id: Id) -> bool:
        """
        :param _id: Node id to be checked
        :return: true if the participant with Id _id is in the leaf committee of the committee overlay
        """
        pass

    @abstractmethod
    def is_member_of_root_committee(self, _id: Id) -> bool:
        """
        :param _id:
        :return: true if the participant with Id _id is member of the root committee withing the tree overlay
        """
        pass

    @abstractmethod
    def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
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
    def leaf_committees(self) -> Set[Committee]:
        pass

    @abstractmethod
    def root_committee(self) -> Committee:
        """
        :return: returns root committee
        """
        pass

    @abstractmethod
    def is_child_of_root_committee(self, _id: Id) -> bool:
        """
        :return: returns child committee/s of root committee if present
        """
        pass

    @abstractmethod
    def leader_super_majority_threshold(self, _id: Id) -> int:
        """
        Amount of distinct number of messages for a node with Id _id member of a committee
        The return value may change depending on which committee the node is member of, including the leader
        :return:
        """
        pass

    @abstractmethod
    def super_majority_threshold(self, _id: Id) -> int:
        pass


class Carnot:
    def __init__(self, _id: Id, overlay=Overlay()):
        self.id: Id = _id
        self.current_view: View = 0
        self.highest_voted_view: View = -1
        self.local_high_qc: Type[Qc] = None
        self.safe_blocks: Dict[Id, Block] = dict()
        self.last_view_timeout_qc: Type[TimeoutQc] = None
        self.overlay: Overlay = overlay

    def can_commit_grandparent(self, block) -> bool:
        # Get the parent block and grandparent block from the safe_blocks dictionary
        parent = self.safe_blocks.get(block.parent())
        grandparent = self.safe_blocks.get(parent.parent())

        # Check if both parent and grandparent exist
        if parent is None or grandparent is None:
            return False

        # Check if the view numbers and QC types match the expected criteria
        is_view_incremented = parent.view == grandparent.view + 1
        is_standard_qc = isinstance(block.qc, StandardQc) and isinstance(parent.qc, StandardQc)

        # Return True if both conditions are met
        return is_view_incremented and is_standard_qc

def latest_committed_view(self) -> View:
    return self.latest_committed_block().view

# Return a list of blocks received by a node for a specific view.
# More than one block is returned only in case of a malicious leader.
def blocks_in_view(self, view: View) -> List[Block]:
    return [block for block in self.safe_blocks.values() if block.view == view]

def genesis_block(self) -> Block:
    return self.blocks_in_view(0)[0]

def latest_committed_block(self) -> Block:
    for view in range(self.current_view, 0, -1):
        for block in self.blocks_in_view(view):
            if self.can_commit_grandparent(block):
                return self.safe_blocks.get(self.safe_blocks.get(block.parent()).parent())
    # The genesis block is always considered committed.
    return self.genesis_block()
