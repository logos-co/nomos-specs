from dataclasses import dataclass
from typing import Union, List, Set
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
