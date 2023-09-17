from dataclasses import dataclass
from typing import Union, List, Set, Optional
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