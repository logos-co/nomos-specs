import itertools
from typing import List, Dict, Tuple, Set, Optional, Self
from carnot import Id, Committee
from overlay import EntropyOverlay
import random


class CarnotTree:
    def __init__(self, nodes: List[Id], number_of_committees: int):
        # inner_commitees: list of tree nodes (int index) matching hashed external committee id
        self.inner_committees: List[Id]
        # membership committees: matching external (hashed) id to the set of members of a committee
        self.membership_committees: Dict[Id, Committee]
        self.inner_committees, self.membership_committees = (
            CarnotTree.build_committee_from_nodes_with_size(
                nodes, number_of_committees
            )
        )
        # committee match between tree nodes and external hashed ids
        self.committees: Dict[Id, int] = {c: i for i, c in enumerate(self.inner_committees)}
        # id (int index) of committee membership by member id
        self.committees_by_member: Dict[Id, int] = {
            member: committee
            for committee, v in self.membership_committees.items()
            for member in v
        }

    @staticmethod
    def build_committee_from_nodes_with_size(
            nodes: List[Id],
            number_of_committees: int,
    ) -> Tuple[List[Id], Dict[int, Committee]]:
        committee_size, remainder = divmod(len(nodes), number_of_committees)
        committees = [
            set(nodes[n*committee_size:(n+1)*committee_size])
            for n in range(0, number_of_committees)
        ]
        # refill committees with extra nodes,
        if remainder != 0:
            cycling_committees = itertools.cycle(committees)
            for node in nodes[-remainder:]:
                next(cycling_committees).add(node)
        committees = [frozenset(s) for s in committees]
        # TODO: This hash method should be specific to what we would want to use for the protocol
        hashes = [hash(s) for s in committees]
        return hashes, dict(enumerate(committees))

    def parent_committee(self, committee_id: Id) -> Optional[Id]:
        # root committee doesnt have a parent
        if committee_id == self.inner_committees[0]:
            return None
        return self.inner_committees[max(self.committees[committee_id] // 2 - 1, 0)]

    def child_committees(self, committee_id: Id) -> Tuple[Optional[Id], Optional[Id]]:
        base = self.committees[committee_id] * 2
        first_child = base + 1
        second_child = base + 2
        return self.inner_committees[first_child], self.inner_committees[second_child]

    def leaf_committees(self) -> Dict[Id, Committee]:
        total_leafs = (len(self.inner_committees) + 1) // 2
        return {
            self.inner_committees[i]: self.membership_committees[i]
            for i in range(len(self.inner_committees) - total_leafs, len(self.inner_committees))
        }

    def root_committee(self) -> Committee:
        return self.membership_committees[0]

    def committee_by_committee_idx(self, committee_idx: int) -> Optional[Committee]:
        return self.membership_committees.get(committee_idx)

    def committee_idx_by_member_id(self, member_id: Id) -> Optional[int]:
        return self.committees_by_member.get(member_id)

    def committee_id_by_member_id(self, member_id: Id) -> Id:
        return self.inner_committees[self.committees_by_member.get(member_id)]

    def committee_by_member_id(self, member_id: Id) -> Optional[Committee]:
        if (committee_idx := self.committee_idx_by_member_id(member_id)) is not None:
            return self.committee_by_committee_idx(committee_idx)


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
        child_parent = self.parent_committee(child)
        parent = self.carnot_tree.committee_by_member_id(parent)
        return child_parent is parent

    def parent_committee(self, _id: Id) -> Optional[Committee]:
        if (parent_id := self.carnot_tree.parent_committee(
                self.carnot_tree.committee_id_by_member_id(_id)
        )) is not None:
            return self.carnot_tree.committee_by_committee_idx(self.carnot_tree.committees[parent_id])

    def leaf_committees(self) -> Set[Committee]:
        return set(self.carnot_tree.leaf_committees().values())

    def root_committee(self) -> Committee:
        return self.carnot_tree.root_committee()

    def is_child_of_root_committee(self, _id: Id) -> bool:
        return self.parent_committee(_id) is self.root_committee()

    def leader_super_majority_threshold(self, _id: Id) -> int:
        committee_size = len(self.carnot_tree.committee_by_member_id(_id))
        return (committee_size * 2 // 3) + 1

    def super_majority_threshold(self, _id: Id) -> int:
        if self.is_member_of_leaf_committee(_id):
            return 0
        committee_size = len(self.carnot_tree.committee_by_member_id(_id))
        return (committee_size * 2 // 3) + 1

