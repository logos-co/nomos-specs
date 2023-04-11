from .carnot import *
from unittest import TestCase


# Unhappy path tests

# 1:  At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
# majority of nodes or a qc higher than th highestQC held by the majority of nodes.
# Majority means more than two thirds of total number of nodes, randomly assigned to committees.


# 2: Have  consecutive view changes and verify the following state variable:
#    last_timeout_view_qc.view
#    high_qc.view
#    current_view
#    last_voted_view

# 3: Due failure consecutive condition between parent and grandparent blocks might not meet. So whenever the
# Consecutive view  condition in the try_to_commit fails, then all the blocks between the latest_committed_block and the
# grandparent (including the grandparent) must be committed in order.
# As far as I know current code only executes the grandparent only. It should also address the case above.


# 4: Have consecutive success adding two blocks then a failure and two consecutive success + 1 failure+ 1 success
# S1 <- S2 <- F1 <- S3 <- S4 <-F2 <- S5
# At S3, S1 should be committed. At S5, S2 and S3 must be committed

class MockCarnot(Carnot):
    def __init__(self, id):
        super(MockCarnot, self).__init__(id)
        self.latest_event = None

    def broadcast(self, block):
        self.latest_event = block

    def send(self, vote: Vote | Timeout | TimeoutQc, *ids: Id):
        self.latest_event = vote

    def rebuild_overlay_from_timeout_qc(self, timeout_qc: TimeoutQc):
        pass


class TestCarnotHappyPath(TestCase):
    @staticmethod
    def add_genesis_block(carnot: Carnot) -> Block:
        genesis_block = Block(view=0, qc=StandardQc(block=b"", view=0), _id=b"")
        carnot.safe_blocks[genesis_block.id()] = genesis_block
        carnot.receive_block(genesis_block)
        carnot.increment_voted_view(0)
        carnot.local_high_qc = genesis_block.qc
        carnot.current_view = 1
        carnot.committed_blocks[genesis_block.id()] = genesis_block
        return genesis_block

    def test_timeout_high_qc(self):
        """
        At the end of the timeout the highQC in the next leader's aggregatedQC should be the highestQC held by the
        majority of nodes or a qc higher than th highestQC held by the majority of nodes.
        Majority means more than two thirds of total number of nodes, randomly assigned to committees.
        """

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
                    int_to_id(1): int_to_id(0),
                    int_to_id(2): int_to_id(0),
                    int_to_id(3): int_to_id(1),
                    int_to_id(4): int_to_id(1)
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
                return {set(leaf) for leaf in self.leafs}

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

        nodes = {int_to_id(i): MockCarnot(int_to_id(i)) for i in range(5)}
        overlay = MockOverlay()
        # add overlay
        for node in nodes.values():
            node.overlay = overlay
        leader: MockCarnot = nodes[int_to_id(0)]
        genesis_block = None
        for node in nodes.values():
            genesis_block = self.add_genesis_block(node)
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
        leader.propose_block(1, genesis_votes)
        proposed_block = leader.latest_event
        self.assertIsNotNone(proposed_block)

        node: MockCarnot
        timeouts = []
        for node in (nodes[int_to_id(_id)] for _id in range(3)):
            node.local_timeout()
            timeouts.append(node.latest_event)

        leader.timeout_detected(timeouts)
        timeout_qc = leader.latest_event

        for node in nodes.values():
            node.received_timeout_qc(timeout_qc)

        # new view votes from leafs
        new_views_leafs_3_4 = [nodes[int_to_id(_id)].latest_event for _id in (3, 4)]
        new_view_leaf_2 = nodes[int_to_id(2)].latest_event

        # new view votes from committee 1 ()
        node_1: MockCarnot = nodes[int_to_id(1)]
        node_1.approve_new_view(new_views_leafs_3_4)
        new_view_1 = node_1.latest_event

        # committee 1 and committee 2 new view votes
        new_views = [new_view_1, new_view_leaf_2]

        # forward root childs votes to root committee (compound of just the leader in this case)
        leader.approve_new_view(new_views)
        root_new_view = leader.latest_event

        leader.propose_block(2, [root_new_view, new_view_1, new_view_leaf_2])

        # Add final assertions on nodes

        new_block_1 = node_1.latest_event
        # Gives an error that AttributeError: 'NewView' object has no attribute 'qc' somehow it returns newView
        # instead of a block
        self.assertEqual(new_block_1.qc.view, 0)

# Assertion should be:
#    last_timeout_view_qc.view should be 1
#    high_qc.view  should be 0
#    current_view  should be 2 (after voting for block)
#    last_voted_view should be 1 before voting and 2 after voting for the block