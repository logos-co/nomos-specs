from typing import List, Dict, Tuple, Set, Optional, Self
from carnot import Id, Committee
from carnot.overlay import EntropyOverlay
import random

class CarnotTree:
    def __int__(self, nodes: List[Id], number_of_committees: int):
        self.number_of_committees = number_of_committees
        self.committee_size = len(nodes) // number_of_committees
        self.inner_committees = CarnotTree.build_committee_from_nodes_with_size(
            nodes, self.number_of_committees, self.committee_size
        )
        self.committees = {k: v for v, k in self.inner_committees.values()}
        self.nodes = CarnotTree.build_nodes_index(nodes, self.committee_size)

    @staticmethod
    def build_committee_from_nodes_with_size(nodes: List[Id], number_of_committees: int, committee_size: int) -> Dict[int, Id]:
        return dict(enumerate([
            # TODO: This hash method should be specific to what we would want to use for the protocol
            hash(frozenset(nodes[slice(n, n+number_of_committees)]))
            for n in range(0, number_of_committees, committee_size)
        ]))

    @staticmethod
    def build_nodes_index(nodes: List[Id], committee_size: int) -> Dict[Id, int]:
        return {
            _id: i // committee_size for i, _id in enumerate(nodes)
        }

    def parent_committee(self, committee_id: Id):
        return self.inner_committees[min(self.committees[committee_id] // 2 - 1, 0)]

    def child_committees(self, committee_id: Id) -> Tuple[Id, Id]:
        base = self.committees[committee_id] * 2
        first_child = base + 1
        second_child = base + 2
        return self.inner_committees[first_child], self.inner_committees[second_child]


class CarnotOverlay(EntropyOverlay):
    def __init__(self, nodes: List[Id], current_leader: Id, entropy: bytes, number_of_committees: int):
        self.entropy = entropy
        self.number_of_committees = number_of_committees
        self.nodes = nodes.copy()
        self.current_leader = current_leader
        random.seed(a=self.entropy, version=2)
        random.shuffle(self.nodes)
        self.carnot_tree = CarnotTree(nodes, number_of_committees)

    def advance(self, entropy: bytes) -> Self:
        return CarnotOverlay(self.nodes, entropy, self.number_of_committees)

    def is_leader(self, _id: Id):
        return _id == self.leader()

    def leader(self) -> Id:
        return self.current_leader

    def next_leader(self) -> Id:
        random.seed(a=self.entropy, version=2)
        return random.choice(self.nodes)

    def is_member_of_leaf_committee(self, _id: Id) -> bool:
        pass

    def is_member_of_root_committee(self, _id: Id) -> bool:
        pass

    def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
        pass

    def parent_committee(self, _id: Id) -> Optional[Committee]:
        pass

    def leaf_committees(self) -> Set[Committee]:
        pass

    def root_committee(self) -> Committee:
        pass

    def is_child_of_root_committee(self, _id: Id) -> bool:
        pass

    def leader_super_majority_threshold(self, _id: Id) -> int:
        pass

    def super_majority_threshold(self, _id: Id) -> int:
        pass