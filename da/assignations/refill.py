from dataclasses import dataclass
from typing import List, Set, TypeAlias, Sequence
from itertools import cycle, chain
from collections import Counter
from heapq import heappush, heappop, heapify

from numpy.f2py.crackfortran import previous_context

DeclarationId:  TypeAlias = bytes
Assignations: TypeAlias = List[Set[DeclarationId]]

@dataclass(order=True)
class Participant:
    # Participants wrapper class
    # Used for keeping ordering in the heap by the participation first and the declaration id second
    participation: int              # prioritize participation count first
    declaration_id: DeclarationId   # sort by id on default

@dataclass
class Subnetwork:
    # Subnetwork wrapper that keeps the subnetwork id [0..2048) and the set of participants in that subnetwork
    participants: Set[DeclarationId]
    subnetwork_id: int

    def __lt__(self, other):
        return (len(self), self.subnetwork_id) < (len(other), other.subnetwork_id)

    def __gt__(self, other):
        return (len(self), self.subnetwork_id) > (len(other), other.subnetwork_id)

    def __len__(self):
        return len(self.participants)


def are_subnetworks_filled_up_to_replication_factor(subnetworks: Sequence[Subnetwork], replication_factor: int) -> bool:
    return all(len(subnetwork) >= replication_factor for subnetwork in subnetworks)

def all_nodes_are_assigned(participants: Sequence[Participant], average_participation: int) -> bool:
    return all(participant.participation > average_participation for participant in participants)


def heappop_next_for_subnetwork(subnetwork: Subnetwork, participants: List[Participant]) -> Participant:
    poped = []
    participant = heappop(participants)
    while participant.declaration_id in subnetwork.participants:
        poped.append(participant)
        participant = heappop(participants)
    for poped in poped:
        heappush(participants, poped)
    return participant

def calculate_subnetwork_assignations(
        new_nodes_list: Sequence[DeclarationId],
        previous_subnets: Assignations,
        replication_factor: int
) -> Assignations:
    # The algorithm works as follows:
    # 1. Remove nodes that are not active from the previous subnetworks assignations
    # 2. Create a heap with the set of active nodes ordered by, primary the number of subnetworks each participant is at
    #    and secondary by the DeclarationId of the participant (ascending order).
    # 3. Create a heap with the subnetworks ordered by the number of participants in each subnetwork
    # 4. If network is decreasing (less availabe nodes than previous nodes), balance subnetworks:
    #    1) Until the biggest subnetwork and the smallest subnetwork size difference is <= 1
    #    2) Pick the biggest subnetwork and migrate half of the nodes difference to the smallest subnetwork
    # 5. Until all subnetworks are filled up to replication factor and all nodes are assigned:
    #    1) pop the subnetwork with the least participants
    #    2) pop the participant with less participations
    #    3) push the participant into the subnetwork and increment its participation count
    #    4) push the participant and the subnetwork into the respective heaps
    # 6. Return the subnetworks ordered by its subnetwork id

    # average participation per node
    average_participation = max((len(previous_subnets) * replication_factor) // len(new_nodes_list), 1)

    # prepare sets
    previous_nodes = set(chain.from_iterable(previous_subnets))
    new_nodes = set(new_nodes_list)
    unavailable_nodes = previous_nodes - new_nodes

    # remove unavailable nodes
    active_assignations = [subnet - unavailable_nodes for subnet in previous_subnets]

    # count participation per assigned node
    assigned_count: Counter[DeclarationId] = Counter(chain.from_iterable(active_assignations))

    # available nodes heap
    available_nodes = [
        Participant(participation=assigned_count.get(_id, 0), declaration_id=_id) for _id in new_nodes
    ]
    heapify(available_nodes)

    # subnetworks heap
    subnetworks = list(
        Subnetwork(participants=subnet, subnetwork_id=subnetwork_id)
        for subnetwork_id, subnet in enumerate(active_assignations)
    )
    heapify(subnetworks)

    # when shrinking the network diversify nodes in major subnetworks into emptier ones
    if len(previous_nodes) > len(new_nodes):
        balance_subnetworks(subnetworks)

    # this method mutates the subnetworks
    fill_subnetworks(available_nodes, subnetworks, average_participation, replication_factor)

    return [subnetwork.participants for subnetwork in sorted(subnetworks, key=lambda x: x.subnetwork_id)]


def fill_subnetworks(
        available_nodes: List[Participant],
        subnetworks: List[Subnetwork],
        average_participation: int,
        replication_factor: int,
):
    while not (
            are_subnetworks_filled_up_to_replication_factor(subnetworks, replication_factor) and
            all_nodes_are_assigned(available_nodes, average_participation)
    ):
        # take less participants subnetwork
        subnetwork = heappop(subnetworks)

        # take less participations declaration not included in the subnetwork
        participant = heappop_next_for_subnetwork(subnetwork, available_nodes)

        # fill into subnetwork
        subnetwork.participants.add(participant.declaration_id)
        participant.participation += 1
        # push to heaps
        heappush(available_nodes, participant)
        heappush(subnetworks, subnetwork)


def balance_subnetworks(
        subnetworks: List[Subnetwork],
):
    while (len(max(subnetworks)) - len(min(subnetworks))) > 1:
        max_subnetwork = max(subnetworks)
        min_subnetwork = min(subnetworks)
        diff_count = (len(max_subnetwork.participants) - len(min_subnetwork.participants)) // 2
        diff_participants = sorted(max_subnetwork.participants - min_subnetwork.participants)
        for i in range(diff_count):
            move_participant = diff_participants.pop(0)
            min_subnetwork.participants.add(move_participant)
            max_subnetwork.participants.remove(move_participant)
    heapify(subnetworks)
