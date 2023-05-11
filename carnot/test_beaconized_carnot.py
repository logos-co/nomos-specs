from typing import Dict, List
from unittest import TestCase
from itertools import chain

from blspy import PrivateKey

from carnot import Id, Carnot, Block, Overlay, Vote, StandardQc, NewView
from carnot.beacon import generate_random_sk, RandomBeacon
from carnot.beconized_carnot import BeaconizedCarnot, BeaconizedBlock
from carnot.overlay import FlatOverlay, EntropyOverlay
from test_unhappy_path import parents_from_childs


def gen_node(sk: PrivateKey, overlay: Overlay):
    node = BeaconizedCarnot(sk, overlay)
    return node.id, node


def succeed(test_case: TestCase, nodes: Dict[Id, BeaconizedCarnot], proposed_block: BeaconizedBlock) -> List[Vote]:
    overlay = FlatOverlay(list(nodes.keys()))
    overlay.set_entropy(proposed_block.beacon.entropy)

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


def fail(test_case: TestCase, nodes: Dict[Id, BeaconizedCarnot], proposed_block: Block) -> List[NewView]:
    overlay = FlatOverlay(list(nodes.keys()))
    overlay.set_entropy(proposed_block.beacon.entropy)
    # broadcast the block
    for node in nodes.values():
        node.receive_block(proposed_block)

    node: BeaconizedCarnot
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


def add_genesis_block(carnot: Carnot) -> Block:
    genesis_block = BeaconizedBlock(view=0, qc=StandardQc(block=b"", view=0), _id=b"", beacon=RandomBeacon(version=0, context=-1, entropy=[], proof=""))
    carnot.safe_blocks[genesis_block.id()] = genesis_block
    carnot.receive_block(genesis_block)
    carnot.local_high_qc = genesis_block.qc
    carnot.current_view = 1
    return genesis_block

def setup_initial_setup(test_case: TestCase, overlay: EntropyOverlay, size: int) -> (Dict[Id, Carnot], Carnot, Block):
    keys = [generate_random_sk() for _ in range(size)]
    nodes = [key.get_g1() for key in keys]
    nodes = dict(gen_node(key, FlatOverlay(nodes)) for key in keys)
    leader: Carnot = nodes[overlay.leader()]
    genesis_block = None
    for node in nodes.values():
        genesis_block = add_genesis_block(node)
    # votes for genesis block
    genesis_votes = set(
        Vote(
            block=genesis_block.id(),
            view=0,
            voter=id,
            qc=StandardQc(
                block=genesis_block.id(),
                view=0
            ),
        ) for id in nodes.keys()
    )
    proposed_block = leader.propose_block(1, genesis_votes).payload
    test_case.assertIsNotNone(proposed_block)
    return nodes, leader, proposed_block

class TestBeaconizedCarnot(TestCase):
    def test_interleave_success_fails(self):
        """
        At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
        majority of nodes or a qc higher than th highestQC held by the majority of nodes.
        Majority means more than two thirds of total number of nodes, randomly assigned to committees.
        """
        leader: BeaconizedCarnot
        nodes, leader, proposed_block = setup_initial_setup(self, overlay, 5)

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

        committed_blocks = [view for view in range(1, 11) if view not in (4, 5, 7, 8)]
        for node in nodes.values():
            for view in committed_blocks:
                self.assertIn(view, [block.view for block in node.committed_blocks().values()])
