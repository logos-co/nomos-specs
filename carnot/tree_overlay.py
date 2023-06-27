import itertools
from typing import List, Dict, Tuple, Set, Optional, Self
from carnot import Id, Committee
from overlay import EntropyOverlay
import random


class CarnotTree:
    def __init__(self, nodes: List[Id], number_of_committees: int):
        self.number_of_committees = number_of_committees
        self.committee_size = len(nodes) // number_of_committees
        self.inner_committees, self.membership_committees = CarnotTree.build_committee_from_nodes_with_size(
            nodes, self.number_of_committees, self.committee_size
        )
        self.committees = {k: v for v, k in self.inner_committees.items()}
        self.nodes = CarnotTree.build_nodes_index(nodes, self.committee_size)
        self.committees_by_member = {
            member: self.inner_committees[committee]
            for committee, v in self.membership_committees.items()
            for member in v
        }

    @staticmethod
    def build_committee_from_nodes_with_size(
            nodes: List[Id],
            number_of_committees: int,
            committee_size: int
    ) -> Tuple[Dict[int, Id], Dict[int, Set[Id]]]:
        committees = [
            # TODO: This hash method should be specific to what we would want to use for the protocol
            set(nodes[n*committee_size:(n+1)*committee_size])
            for n in range(0, number_of_committees)
        ]
        # TODO: for now simples solution is make latest committee bigger
        remainder = len(nodes) % committee_size
        remainder_nodes = set(nodes[-remainder:])
        committees[number_of_committees-1] |= remainder_nodes
        committees = [frozenset(s) for s in committees]

        hashes = [hash(s) for s in committees]
        return dict(enumerate(hashes)), dict(enumerate(committees))

    @staticmethod
    def build_nodes_index(nodes: List[Id], committee_size: int) -> Dict[Id, int]:
        return {
            _id: i // committee_size for i, _id in enumerate(nodes)
        }

    def parent_committee(self, committee_id: Id) -> Optional[Id]:
        return self.inner_committees[min(self.committees[committee_id] // 2 - 1, 0)]

    def child_committees(self, committee_id: Id) -> Tuple[Optional[Id], Optional[Id]]:
        base = self.committees[committee_id] * 2
        first_child = base + 1
        second_child = base + 2
        return self.inner_committees[first_child], self.inner_committees[second_child]

    def leaf_committees(self) -> Dict[Id, Committee]:
        total_leafs = (self.number_of_committees + 1) // 2
        return {
            self.inner_committees[i]: self.membership_committees[i]
            for i in range(self.number_of_committees - total_leafs, self.number_of_committees)
        }

    def root_committee(self) -> Committee:
        return self.membership_committees[0]

    def committee_by_committee_id(self, committee_id: Id) -> Optional[Committee]:
        return self.membership_committees.get(self.inner_committees[committee_id])

    def committee_by_member_id(self, member_id: Id) -> Id:
        return self.committees_by_member[member_id]


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
        return CarnotOverlay(self.nodes, self.next_leader(), entropy, self.number_of_committees)

    def is_leader(self, _id: Id):
        return _id == self.leader()

    def leader(self) -> Id:
        return self.current_leader

    def next_leader(self) -> Id:
        random.seed(a=self.entropy, version=2)
        return random.choice(self.nodes)

    def is_member_of_leaf_committee(self, _id: Id) -> bool:
        return _id in set(itertools.chain.from_iterable(self.carnot_tree.leaf_committees().values()))

    def is_member_of_root_committee(self, _id: Id) -> bool:
        return _id in self.carnot_tree.root_committee()

    def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
        l, r = self.carnot_tree.child_committees(parent)
        l = self.carnot_tree.committee_by_committee_id(l) if l is not None else set() or set()
        r = self.carnot_tree.committee_by_committee_id(r) if r is not None else set() or set()
        return child in l.join(r)

    def parent_committee(self, _id: Id) -> Optional[Committee]:
        return self.carnot_tree.committee_by_committee_id(
            self.carnot_tree.parent_committee(
                self.carnot_tree.committee_by_member_id(_id)
            )
        )

    def leaf_committees(self) -> Set[Committee]:
        return set(self.carnot_tree.leaf_committees().values())

    def root_committee(self) -> Committee:
        return self.carnot_tree.root_committee()

    def is_child_of_root_committee(self, _id: Id) -> bool:
        return _id in self.root_committee()

    def leader_super_majority_threshold(self, _id: Id) -> int:
        return (self.carnot_tree.committee_size * 2 // 3) + 1

    def super_majority_threshold(self, _id: Id) -> int:
        if self.is_member_of_leaf_committee(_id):
            return 0
        return (self.carnot_tree.committee_size * 2 // 3) + 1

