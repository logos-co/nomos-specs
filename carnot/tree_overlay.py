import itertools
from hashlib import blake2b
from typing import List, Dict, Tuple, Set, Optional, Self
from carnot.carnot import Id, Committee
from carnot.overlay import EntropyOverlay
import random


def blake2b_hash(committee: Committee) -> bytes:
    hasher = blake2b(digest_size=32)
    for member in sorted(committee):
        hasher.update(member)
    return hasher.digest()


class CarnotTree:
    """
    This balanced binary tree implementation uses a combination of indexes and keys to easily calculate parenting
    committee relationships. It also has caching on different kind of access to conveniently retrieve the committees
    based on:
        * Member of a committee
        * Committee id (hash)

    It is composed of `inner_committees`, an array that matches a binary tree node distribution:
          0,  1,  2,  3..
        [c0, c1, c2, c3  ]
        where `cX` is the committee id (hash of the set with the committee members ids)
    The number of leafs in the committee is calculated with:
        total_leafs = (len(inner_committees) + 1) // 2
    Parenting relation can be calculated for a committee index (idx) with:
        parent_committee_idx = committee_idx // 2 - 1
    Children relation is calculated with those indexes (idx) as well:
        left_child, right_child = (committee_idx*2 + 1, committee_idx*2 + 2)

    Then we have some dictionaries/maps that matches different information to those indexes:
        * `membership_committees`: matches committee idx to the actual committee set of participants
        * `committee_id_to_index`: matches committee id (hash) to committee index (idx) in `inner_committees`
        * `committee_by_member`: matches member id to the committee id that is a member from
    """
    def __init__(self, nodes: List[Id], number_of_committees: int):
        # useless to build an overlay with no committees
        assert number_of_committees > 0
        # inner_committees: list of tree nodes (int index) matching hashed external committee id
        self.inner_committees: List[Id]
        # membership committees: matching committee idx to the set of members of a committee
        self.membership_committees: Dict[int, Committee]
        self.inner_committees, self.membership_committees = (
            CarnotTree.build_committee_from_nodes_with_size(
                nodes, number_of_committees
            )
        )
        # committee match between tree nodes and external hashed ids
        self.committee_id_to_index: Dict[Id, int] = {c: i for i, c in enumerate(self.inner_committees)}
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

        hashes = [blake2b_hash(s) for s in committees]
        committees = [frozenset(s) for s in committees]

        return hashes, dict(enumerate(committees))

    def parent_committee(self, committee_id: Id) -> Optional[Id]:
        # root committee doesnt have a parent
        if committee_id == self.inner_committees[0]:
            return None
        return self.inner_committees[max(self.committee_id_to_index[committee_id] // 2 - 1, 0)]

    def child_committees(self, committee_id: Id) -> Tuple[Optional[Id], Optional[Id]]:
        base = self.committee_id_to_index[committee_id] * 2
        committees_size = len(self.inner_committees)
        first_child = base + 1
        second_child = base + 2
        first_child = self.inner_committees[first_child] if first_child < committees_size else None
        second_child = self.inner_committees[second_child] if second_child < committees_size else None
        return first_child, second_child

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

    def committee_by_committee_id(self, committee_id: Id) -> Optional[Committee]:
        if (committee_idx := self.committee_id_to_index.get(committee_id)) is not None:
            return self.committee_by_committee_idx(committee_idx)

    def parent_committee_from_member_id(self, _id):
        if (parent_id := self.parent_committee(
                self.committee_id_by_member_id(_id)
        )) is not None:
            return self.committee_by_committee_idx(self.committee_id_to_index[parent_id])


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
        return child_parent == parent

    def parent_committee(self, _id: Id) -> Optional[Committee]:
        self.carnot_tree.parent_committee_from_member_id(_id)

    def leaf_committees(self) -> Set[Committee]:
        return set(self.carnot_tree.leaf_committees().values())

    def root_committee(self) -> Committee:
        return self.carnot_tree.root_committee()

    def is_child_of_root_committee(self, _id: Id) -> bool:
        return self.parent_committee(_id) == self.root_committee()

    def leader_super_majority_threshold(self, _id: Id) -> int:
        root_committee = self.carnot_tree.inner_committees[0]
        childs = self.carnot_tree.child_committees(root_committee)
        childs_size = sum(
            len(committee) for c in childs
            if (committee := self.carnot_tree.committee_by_committee_id(c)) is not None
        )
        root_committee_size = len(self.root_committee())
        committee_size = root_committee_size + childs_size
        return (committee_size * 2 // 3) + 1

    def super_majority_threshold(self, _id: Id) -> int:
        if self.is_member_of_leaf_committee(_id):
            return 0
        committee_size = len(self.carnot_tree.committee_by_member_id(_id))
        return (committee_size * 2 // 3) + 1
