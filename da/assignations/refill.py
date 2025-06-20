from dataclasses import dataclass
from typing import List, Set, TypeAlias, Sequence
from itertools import cycle, chain
from collections import Counter
from heapq import heappush, heappop, heapify

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
        return len(self) < len(other)

    def __len__(self):
        return len(self.participants)



def are_subnetworks_filled_up_to_replication_factor(subnetworks: Sequence[Subnetwork], replication_factor: int) -> bool:
    return all(len(subnetwork) >= replication_factor for subnetwork in subnetworks)

def all_nodes_are_assigned(participants: Sequence[Participant]) -> bool:
    return all(participant.participation > 0 for participant in participants)


def heappop_next_for_participant(subnetworks: List[Subnetwork], participant: Participant) -> Subnetwork:
    filtered = [subnetwork for subnetwork in subnetworks if participant.declaration_id not in subnetwork.participants]
    poped = heappop(filtered)
    subnetworks.remove(poped)
    heapify(subnetworks)
    return poped

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
    # 4. Until all subnetworks are filled up to replication factor and all nodes are assigned:
    #    1) pop the subnetwork with the least participants
    #    2) pop the participant with less participations
    #    3) push the participant into the subnetwork and increment its participation count
    #    4) push the participant and the subnetwork into the respective heaps
    # 5. Return the subnetworks ordered by its subnetwork id

    # prepare sets
    previous_nodes =  set(chain.from_iterable(previous_subnets))
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


    while not (
        are_subnetworks_filled_up_to_replication_factor(subnetworks, replication_factor) and
        all_nodes_are_assigned(available_nodes)
    ):
        # take less participations declaration
        participant = heappop(available_nodes)

        # take less participants subnetwork
        subnetwork = heappop(subnetworks)

        # fill into subnetwork
        subnetwork.participants.add(participant.declaration_id)
        participant.participation += 1
        # push to queues
        heappush(available_nodes, participant)
        heappush(subnetworks, subnetwork)
    return [subnetwork.participants for subnetwork in sorted(subnetworks, key=lambda x: x.subnetwork_id)]




if __name__ == "__main__":
    import random
    number_of_columns = 4096
    for size in [100, 500, 1000, 10000]:
        nodes_ids = [random.randbytes(32) for _ in range(size)]
        replication_factor = 3
        print(size, replication_factor)
        # print(a := calculate_subnets(nodes_ids, number_of_columns, replication_factor))
        from pprint import pprint
        b = calculate_subnetwork_assignations(nodes_ids, [set() for _ in range(number_of_columns)], replication_factor)
        # pprint(b)
        assert len(set(chain.from_iterable(b))) == len(nodes_ids)
        # fill up new nodes
        for i in range(0, size, 5):
            nodes_ids[i] = random.randbytes(32)
        b = calculate_subnetwork_assignations(nodes_ids, b, replication_factor)
        # pprint(b)
        assert len(set(chain.from_iterable(b))) == len(nodes_ids), f"{len(set(chain.from_iterable(b)))} != {len(nodes_ids)}"
        print(Counter(chain.from_iterable(b)).values())

