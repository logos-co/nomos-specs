from carnot.carnot import *
from unittest import TestCase
from itertools import chain


class MockCarnot(Carnot):
    def __init__(self, id):
        super(MockCarnot, self).__init__(id)

    def rebuild_overlay_from_timeout_qc(self, timeout_qc: TimeoutQc):
        pass


class MockOverlay(Overlay):
    """
    Overlay for 5 nodes where the leader is the single member of the root committee
            0
            │
        1◄──┴──►2
        │
     3◄─┴─►4
    """

    def __init__(self):
        self.parents = {
            int_to_id(1): {int_to_id(0)},
            int_to_id(2): {int_to_id(0)},
            int_to_id(3): {int_to_id(1)},
            int_to_id(4): {int_to_id(1)}
        }

        self.childs = {
            int_to_id(0): {
                int_to_id(1), int_to_id(2)
            },
            int_to_id(1): {
                int_to_id(3), int_to_id(4)
            }
        }

        self.leafs = {
            int_to_id(2), int_to_id(3), int_to_id(4)
        }

    def leaf_committees(self) -> Set[Committee]:
        return [[leaf] for leaf in self.leafs]

    def root_committee(self) -> Committee:
        return {int_to_id(0)}

    def is_child_of_root_committee(self, _id: Id) -> bool:
        return _id in {int_to_id(1), int_to_id(2)}

    def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
        return child in childs if (childs := self.childs.get(parent)) else False

    def leader_super_majority_threshold(self, _id: Id) -> int:
        return 3

    def is_leader(self, _id: Id):
        # Leader is the node with id 0, otherwise not
        return _id == int_to_id(0)

    def is_member_of_root_committee(self, _id: Id):
        return _id == int_to_id(0)

    def leader(self, view: View) -> Id:
        return int_to_id(0)

    def parent_committee(self, _id: Id) -> Optional[Committee]:
        return self.parents.get(_id)

    def is_member_of_leaf_committee(self, _id: Id) -> bool:
        return _id in self.leafs

    def super_majority_threshold(self, _id: Id) -> int:
        thresholds = {
            int_to_id(0): 2,
            int_to_id(1): 2,
        }
        return thresholds.get(_id, 0)


def add_genesis_block(carnot: Carnot) -> Block:
    genesis_block = Block(view=0, qc=StandardQc(block=b"", view=0), _id=b"")
    carnot.safe_blocks[genesis_block.id()] = genesis_block
    carnot.receive_block(genesis_block)
    carnot.local_high_qc = genesis_block.qc
    carnot.current_view = 1
    return genesis_block


def initial_setup(test_case: TestCase, overlay: MockOverlay, size: int) -> (Dict[Id, Carnot], MockCarnot, Block):
    nodes = {int_to_id(i): MockCarnot(int_to_id(i)) for i in range(size)}
    # add overlay
    for node in nodes.values():
        node.overlay = overlay
    leader: MockCarnot = nodes[overlay.leader(0)]
    genesis_block = None
    for node in nodes.values():
        genesis_block = add_genesis_block(node)
    # votes for genesis block
    genesis_votes = set(
        Vote(
            block=genesis_block.id(),
            view=0,
            voter=int_to_id(i),
            qc=StandardQc(
                block=genesis_block.id(),
                view=0
            ),
        ) for i in range(5)
    )
    proposed_block = leader.propose_block(1, genesis_votes).payload
    test_case.assertIsNotNone(proposed_block)
    return nodes, leader, proposed_block


def parents_from_childs(overlay: MockOverlay, childs: List[Id]) -> Set[Id]:
    if len(childs) == 0:
        return set()
    possible_parents = filter(
        lambda x: x is not None,
        chain.from_iterable(parent for _id in childs if (parent := overlay.parent_committee(_id)))
    )
    return set(possible_parents) if possible_parents else set()


def succeed(test_case: TestCase, overlay: Overlay, nodes: Dict[Id, Carnot], proposed_block: Block) -> List[Vote]:
    # broadcast the block
    for node in nodes.values():
        node.receive_block(proposed_block)

    votes = {}
    childs_ids = list(chain.from_iterable(overlay.leaf_committees()))
    leafs = [nodes[_id] for _id in childs_ids]
    for node in leafs:
        vote = node.approve_block(proposed_block, set()).payload
        votes[node.id] = vote

    while len(parents := parents_from_childs(overlay, childs_ids)) != 0:
        for node_id in parents:
            node = nodes[node_id]
            child_votes = [votes[_id] for _id in votes.keys() if overlay.is_member_of_child_committee(node_id, _id)]
            if len(child_votes) == overlay.super_majority_threshold(node_id) and node_id not in votes:
                vote = node.approve_block(proposed_block, child_votes).payload
                votes[node_id] = vote
        childs_ids = list(set(parents))

    root_votes = [
        votes[node_id]
        for node_id in nodes
        if overlay.is_member_of_root_committee(node_id) or overlay.is_child_of_root_committee(node_id)
    ]
    return root_votes


def fail(test_case: TestCase, overlay: Overlay, nodes: Dict[Id, Carnot], proposed_block: Block) -> List[NewView]:
    # broadcast the block
    for node in nodes.values():
        node.receive_block(proposed_block)

    node: MockCarnot
    timeouts = []
    for node in (nodes[_id] for _id in nodes if overlay.is_member_of_root_committee(_id) or overlay.is_child_of_root_committee(_id)):
        timeout = node.local_timeout().payload
        timeouts.append(timeout)

    root_member = next(nodes[_id] for _id in nodes if overlay.is_member_of_root_committee(_id))
    timeout_qc = root_member.timeout_detected(timeouts).payload

    for node in nodes.values():
        node.receive_timeout_qc(timeout_qc)

    votes = {}
    childs_ids = list(chain.from_iterable(overlay.leaf_committees()))
    leafs = [nodes[_id] for _id in childs_ids]
    for node in leafs:
        vote = node.approve_new_view(timeout_qc, set()).payload
        votes[node.id] = vote

    while len(parents := parents_from_childs(overlay, childs_ids)) != 0:
        for node_id in parents:
            node = nodes[node_id]
            child_votes = [votes[_id] for _id in votes.keys() if overlay.is_member_of_child_committee(node_id, _id)]
            if len(child_votes) == overlay.super_majority_threshold(node_id) and node_id not in votes:
                vote = node.approve_new_view(timeout_qc, child_votes).payload
                votes[node_id] = vote
        childs_ids = list(set(parents))

    root_votes = [
        votes[node_id]
        for node_id in nodes
        if overlay.is_member_of_root_committee(node_id) or overlay.is_child_of_root_committee(node_id)
    ]
    return root_votes


class TestCarnotUnhappyPath(TestCase):

    def test_timeout_high_qc(self):
        """
        At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
        majority of nodes or a qc higher than th highestQC held by the majority of nodes.
        Majority means more than two thirds of total number of nodes, randomly assigned to committees.
        """

        overlay = MockOverlay()

        nodes, leader, proposed_block = initial_setup(self, overlay, 5)

        # In this loop 'view' is the view that fails
        for view in range(1, 4, 2):
            # When view v fails, a timeout qc is built for view v and nodes jump to view v + 1
            # while aggregating votes for the high qc. Those votes are then forwarded to the leader of view v + 2
            # which can propose a block with those aggregate votes as proof of the previous round completion.
            root_votes = fail(self, overlay, nodes, proposed_block)
            proposed_block = leader.propose_block(view+2, root_votes).payload

            # Add final assertions on nodes
            # Thus, the first block that can be proposed is 2 views after the timeout
            self.assertEqual(proposed_block.view, view + 2)
            # Its qc is always for the view before the block is proposed for
            self.assertEqual(proposed_block.qc.view, view + 1)
            # The high qc is 0, since we never had a successful round
            self.assertEqual(proposed_block.qc.high_qc().view, 0)
            self.assertEqual(leader.last_view_timeout_qc.view, view)
            self.assertEqual(leader.local_high_qc.view, 0)
            self.assertEqual(leader.highest_voted_view, view+1)

        for node in nodes.values():
            self.assertEqual(node.latest_committed_view(), 0)

    def test_interleave_success_fails(self):
        """
        At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
        majority of nodes or a qc higher than th highestQC held by the majority of nodes.
        Majority means more than two thirds of total number of nodes, randomly assigned to committees.
        """
        overlay = MockOverlay()
        leader: MockCarnot
        nodes, leader, proposed_block = initial_setup(self, overlay, 5)

        for view in range(2, 5):
            root_votes = succeed(self, overlay, nodes, proposed_block)
            proposed_block = leader.propose_block(view, root_votes).payload

        root_votes = fail(self, overlay, nodes, proposed_block)
        proposed_block = leader.propose_block(6, root_votes).payload

        for view in range(7, 8):
            root_votes = succeed(self, overlay, nodes, proposed_block)
            proposed_block = leader.propose_block(view, root_votes).payload

        root_votes = fail(self, overlay, nodes, proposed_block)
        proposed_block = leader.propose_block(9, root_votes).payload

        for view in range(10, 15):
            root_votes = succeed(self, overlay, nodes, proposed_block)
            proposed_block = leader.propose_block(view, root_votes).payload

        committed_blocks = {0, 1, 2, 3, 6, 9, 10, 11}
        for node in nodes.values():
            self.assertEqual(committed_blocks, {block.view for block in node.committed_blocks().values()})
