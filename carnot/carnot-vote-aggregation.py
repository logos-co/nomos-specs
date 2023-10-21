from dataclasses import dataclass
from typing import Union, List, Set, Optional, Type, TypeAlias, Dict
from abc import ABC, abstractmethod

import carnot
from carnot import Carnot, Overlay, Qc, Block, TimeoutQc, AggregateQc, Vote, Event, Send, Timeout, Quorum, NewView, \
    BroadCast, Id, Committee, View, StandardQc, int_to_id



class Overlay2(Overlay):
    """
    Overlay structure for a View
    """

    @abstractmethod
    def is_member_of_my_committee(self, _id: Id) -> bool:
        """
        :param _id:
        :return: true if the participant with Id _id is member of the committee of the  verifying node withing the tree overlay
        """
        pass

    def is_member_of_subtree(self, root_node: Id, child: Id) -> bool:
        """
        :param root_node:
        :param child:
        :return: true if participant with Id  is member of a committee in the subtree of the participant with Id root_node
        """
        pass

    @abstractmethod
    def my_committee(self, _id: Id) -> Optional[Committee]:
        """
        :param _id:
        :return: Some(committee) of the participant with Id _id withing the committee tree overlay
        """
        pass

    @abstractmethod
    def leader_super_majority_threshold(self, _id: Id) -> int:
        """
        This corresponds to a threshold of 2n/3 + 1, where 'n' represents the total number of network participants.
        :return:
        """
        pass

    @abstractmethod
    def super_majority_threshold(self, _id: Id) -> int:
        """
        This corresponds to a threshold of 2n_c/3 ( 2n_c/3 +1 for root committee of the overlay), where n_c represents
        the total number of participants in the subtree of the overlay that includes the node with the ID 'Id' in its root committee of the subtree.
        return:
        """
        pass

    def number_of_committees(self) -> int:
        """
        :return: returns total number of committees in the overlay.
        """
        pass


class Carnot2(Carnot):
    def __init__(self, _id: Id, overlay=Overlay2()):
        self.latest_committed_block = None
        self.id: Id = _id
        self.current_view: View = 0
        self.highest_voted_view: View = -1
        self.local_high_qc: Type[Qc] = None
        self.safe_blocks: Dict[Id, Block] = dict()
        self.last_view_timeout_qc: Type[TimeoutQc] = None
        self.overlay: Overlay = overlay

    def can_commit_grandparent(self, block: carnot.Block) -> bool:
        # Get the parent block and grandparent block from the safe_blocks dictionary
        parent = self.safe_blocks.get(block.parent())
        grandparent = self.safe_blocks.get(parent.parent())

        # Check if both parent and grandparent exist
        if parent is None or grandparent is None:
            return False

        # Check if the view numbers and QC types match the expected criteria
        is_view_incremented = parent.view == grandparent.view + 1
        is_standard_qc = isinstance(block.qc, StandardQc) and isinstance(parent.qc, StandardQc)

        # Return True if both conditions are met
        return is_view_incremented and is_standard_qc

    @abstractmethod
    def commit_block(self, block: Block) -> bool:
        pass

    def commit_the_chain(self, grand_parent: Block):
        # Create an empty stack to store the blocks in reverse order
        block_stack = []

        # Start with the grand_parent block
        current_block = grand_parent

        # Push blocks onto the stack until we reach the parent of the latest_committed_block
        while current_block != self.latest_committed_block.parent():
            block_stack.append(current_block)
            current_block = self.safe_blocks.get(current_block.parent())
        # Pop and commit blocks from the stack to execute them in order
        while block_stack:
            block_to_commit = block_stack.pop()
            # Commit the transactions of the block using your commit_block method
            self.commit_block(block_to_commit)
        latest_committed_block = block_to_commit
        # Update the latest committed block to be the latest_committed_block
        self.latest_committed_block = latest_committed_block

    # The  check for the first block generated after unhappy path is added.
    def block_is_safe(self, block: Block) -> bool:
        if isinstance(block.qc, StandardQc):
            return block.view_num == block.qc.view() + 1
        elif isinstance(block.qc, AggregateQc):
            return block.view_num == block.qc.view() + 1 and block.extends(self.latest_committed_block())
        else:
            return False

    def update_high_qc(self, qc: Qc):
        match (self.local_high_qc, qc):
            case (None, new_qc) if isinstance(new_qc, StandardQc):
                # Set local high QC to the new StandardQc
                self.local_high_qc = new_qc
            case (None, new_qc) if isinstance(new_qc, AggregateQc):
                # Set local high QC to the high QC from the new AggregateQc
                self.local_high_qc = new_qc.high_qc()
            case (old_qc, new_qc) if isinstance(new_qc, StandardQc) and new_qc.view > old_qc.view:
                # Update local high QC if the new StandardQc has a higher view
                self.local_high_qc = new_qc
            case (old_qc, new_qc) if isinstance(new_qc,
                                                AggregateQc) and new_qc.high_qc().view != old_qc.view and new_qc.view > old_qc.view:
                # Update local high QC if the view of the high QC in the new AggregateQc is different
                self.local_high_qc = new_qc.high_qc()

        # If my view is not updated, I update it when I see a QC for that view
        # If there is any missing blocks then these blocks should be downloaded.
        if qc.view >= self.current_view:
            self.current_view = qc.view + 1

    # Feel free to remove, just added for simplicity.
    def update_timeout_qc(self, timeout_qc: TimeoutQc):
        if not self.last_view_timeout_qc or timeout_qc.view > self.last_view_timeout_qc.view:
            self.last_view_timeout_qc = timeout_qc

    def approve_block(self, block: Block, votes: Set[Vote]) -> Event:
        # Assertions for input validation
        assert block.id() in self.safe_blocks
        # This assertion will be moved outside as the approve_block will be called in two cases:
        # 1st the fast path when len(votes) == self.overlay.super_majority_threshold(self.id) and the second
        # When there is the first timeout t1 for the fast path and the protocol operates in the slower path
        # in this case the node will prepare a QC from votes it has received.
        # assert len(votes) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_subtree(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)
        assert self.highest_voted_view < block.view

        # Create a QC based on committee membership
        qc = self.build_qc(block.view, block, None)  # if self.overlay.is_member_of_root_committee(self.id) else None

        # Create a new vote
        vote = Vote(
            block=block.id(),
            voter=self.id,
            view=block.view,
            qc=qc
        )

        # Update the highest voted view
        self.highest_voted_view = max(self.highest_voted_view, block.view)

        # After block verification, votes are sent to committee members.
        # When a QC is formed from 2/3rd of subtree votes, it's forwarded to the parent committee.
        # If a Type 1 timeout occurs, a QC is built from available votes and QCs and sent to the parent.
        # Subsequent votes are forwarded to the parent committee members.
        if self.overlay.is_member_of_root_committee():
            recipient = self.overlay.leader(block.view + 1)
        else:
            recipient = self.overlay.my_committee(self.id)

        # Return a Send event to the appropriate recipient
        return Send(to=recipient, payload=vote)

    # A committee member builds a QC or timeout QC with at least two-thirds of votes from its sub-branch within the
    # overlay. Furthermore, if a node builds a timeout QC with at least f+1 timeout messages, it forwards them to its
    # parents as well as the child committee. This allows any node that have not timed out to timeout.
    def build_qc(self, view: int, qc: Optional[Qc], t_qc: Optional[TimeoutQc], block: Optional[Block] = None,
                 Timeouts: Optional[Set[Timeout]] = None,
                 votes: Optional[List[Vote]] = None) -> Qc:

        if Timeouts or TimeoutQc:
            # Create a list to hold  timeout messages that are not repeated in the timeout qc
            uniq_timeout_messages = []

            # Create a set to store sender IDs from TimeoutQc (if it's not None)
            timeout_qc_sender_ids = set()
            if TimeoutQc:
                timeout_qc_sender_ids = TimeoutQc.sender_ids

            # Iterate over Timeout messages and add them to uniq_timeout_messages if their sender's ID is not in the timeout_qc_sender_ids set
            if Timeouts:
                for timeout_msg in Timeouts:
                    # Check if the sender's ID is not in the sender_ids set of TimeoutQc
                    if timeout_msg.sender not in timeout_qc_sender_ids:
                        uniq_timeout_messages.append(timeout_msg)

            # Calculate the highest_qc by finding the maximum high_qc.view value
            highest_qc_timeouts = max(uniq_timeout_messages, key=lambda x: x.high_qc.view).high_qc
            highest_qc = max(highest_qc_timeouts,TimeoutQc.high_qc)

            # Create an AggregateQc using all timeout messages
            return AggregateQc(
                qcs=[msg.high_qc.view for msg in uniq_timeout_messages]+TimeoutQc.qc_views,
                highest_qc=highest_qc,
                view=uniq_timeout_messages[0].view if uniq_timeout_messages else (TimeoutQc.view if TimeoutQc else 0)
            )

        else:
            # Happy path: Standard QC
            if votes:
                # Use vote.block if votes are available
                block_id = votes[0].block
            elif block:
                # Use the provided block if votes are not available
                block_id = block.id()
            elif qc:
                block_id = qc.block
            else:
                # No block or votes provided, return None
                return None

            return StandardQc(
                view=view,
                block=block_id
            )

    # A node initially forwards a vote or qc from its subtree to its parent committee. There can be two instances this
    # can happen: 1: If a node forms a QC qc from votes and QCs it receives from its subtree such that the total number of votes in the qc is at two-third of votes from the subtree, then
    # it forwards this QC to the parent committee members or a subset of parent committee members.
    # 2: After sending the qc any additional votes are forwarded to the parent committee members or a subset of parent committee members.
    # 3: After type 1 timeout a node builds a QC from arbitrary number of votes+QCs it has received, building a QC qc such that total number of votes in qc is less
    # than the two-thirds of the number of the nodes in the sub-tree.

    def forward_vote_qc(self, vote: Optional[Vote] = None, qc: Optional[Qc] = None) -> Optional[Event]:
        # Assertions for input validation if vote is provided
        if vote:
            assert vote.block in self.safe_blocks
            assert self.overlay.is_member_of_subtree(self.id, vote.voter), "Voter should be a member of the subtree"
            assert self.highest_voted_view == vote.view, "Can only forward votes after voting ourselves"

        # Assertions for input validation if QC is provided
        if qc:
            assert qc.view >= self.current_view, "QC view should be greater than or equal to the current view"
            assert all(
                self.overlay.is_member_of_subtree(self.id, voter)
                for voter in qc.voters
            ), "All voters in QC should be members of the subtree"

        if self.overlay.is_member_of_root_committee(self.id):
            # Forward the vote or QC to the next leader in the root committee
            recipient = self.overlay.next_leader()
        else:
            # Forward the vote or QC to the parent committee
            recipient = self.overlay.parent_committee

        # Create a Send event with either vote or QC as payload and return it
        if vote:
            return Send(to=recipient, payload=vote)
        elif qc:
            return Send(to=recipient, payload=qc)
        else:
            # If neither vote nor QC is provided, return None
            return None

    # A node may receive QCs from child committee members. It may also build it's own QC.
    # These QCs are then concatenated into one before sending to the parent committee.
    def concatenate_standard_qcs(qc_set: Set[StandardQc]) -> StandardQc:
        # Initialize the attributes for the concatenated StandardQc
        concatenated_block = None
        concatenated_view = None
        concatenated_voters = set()

        # Iterate through the input set of StandardQc objects
        for qc in qc_set:
            concatenated_voters.update(qc.voters)

        # Choose the block and view values from the first StandardQc in the set
        if qc_set:
            concatenated_block = qc_set[0].block
            concatenated_view = qc_set[0].view

        # Create the concatenated StandardQc object
        concatenated_qc = StandardQc(concatenated_block, concatenated_view, concatenated_voters)

        return concatenated_qc




    # 1: Similarly, if a node receives timeout QC and timeout messages, it builds a timeout qc (TC) representing 2/3 of timeout messages from its subtree,
    # then it forwards it to the parent committee members or a subset of parent committee members.
    # 2: It type 1 timeout occurs and the node haven't collected enough timeout messages, it can simply build a QC from whatever timeout messages it has
    # and forward the QC to its parent.
    # 3: Any additional timeout messages are forwarded to the parent committee members or a subset of parent committee members.

    def forward_timeout_qc(self, msg: TimeoutQc) -> Optional[Event]:
        # Assertions for input validation
        assert msg.view == self.current_view, "Received TimeoutQc with correct view"
        assert self.overlay.is_member_of_subtree(self.id, msg.sender)
        assert self.highest_voted_view == msg.view, "Can only forward NewView after voting ourselves"

        if self.overlay.is_member_of_root_committee(self.id):
            # Forward the NewView message to the next leader in the root committee
            return Send(to=self.overlay.next_leader(), payload=msg)
        else:
            # Forward the NewView message to the parent committee
            return Send(to=self.overlay.parent_committee, payload=msg)

    def propose_block(self, view: View, quorum: Quorum) -> Event:
        # Check if the node is a leader and if the quorum size is sufficient
        assert self.overlay.is_leader(self.id), "Only leaders can propose blocks"
        assert len(quorum) >= self.overlay.leader_super_majority_threshold(self.id), "Sufficient quorum size is allowed"

        # Initialize QC to None
        qc = None

        # Extract the first element from the quorum
        first_quorum_item = quorum[0]

        if isinstance(first_quorum_item, Vote):
            # Happy path: Create a QC based on votes in the quorum
            vote = first_quorum_item
            assert vote.block in self.safe_blocks
            qc = self.build_qc(vote.view, self.safe_blocks[vote.block], None)
        elif isinstance(first_quorum_item, NewView):
            # Unhappy path: Create a QC based on NewView messages in the quorum
            new_view = first_quorum_item
            qc = self.build_qc(new_view.view, None, quorum)

        # Generate a new Block with a dummy ID for proposing the next block
        block = Block(
            view=view,
            qc=qc,
            # Dummy ID for proposing the next block
            _id=int_to_id(hash((f"View-{view}", f"QC-View-{qc.view}")))
        )

        # Return a Broadcast event with the proposed block
        return BroadCast(payload=block)

    def local_timeout(self) -> Optional[Event]:
        """
        Root committee changes for each failure, so repeated failure will be handled by different
        root committees
        """
        # avoid voting after we timeout
        self.highest_voted_view = self.current_view

        timeout_msg: Timeout = Timeout(
            view=self.current_view,
            high_qc=self.local_high_qc,
            # local_timeout is only true for the root committee or members of its children
            # root committee or its children can trigger the timeout.
            timeout_qc=self.last_view_timeout_qc,
            sender=self.id
        )
        return Send(payload=timeout_msg, to=self.overlay.my_committee())

    def receive_timeout_qc(self, timeout_qc: TimeoutQc):
        if timeout_qc.view < self.current_view:
            # Ignore outdated timeout QC
            return

        # Update the local high QC with the new high QC from the timeout QC
        self.update_high_qc(timeout_qc.high_qc)

        # Update the last view timeout QC
        self.update_timeout_qc(timeout_qc)

        # Update the current view based on the timeout QC
        self.update_current_view_from_timeout_qc(timeout_qc)

        # Optionally, rebuild the overlay from the timeout QC
        # self.rebuild_overlay_from_timeout_qc(timeout_qc)

    # The overlay can be built using a random seed for any random source.
    # Here we assume the TimeoutQC is the seed.
    def rebuild_overlay_from_timeout_qc(self, timeout_qc: TimeoutQc):
        # Ensure the timeout QC view is greater than or equal to the current view
        assert timeout_qc.view >= self.current_view, "Timeout QC view should be greater than or equal to current view"

        # Rebuild the overlay from scratch
        self.overlay = Overlay()

    @staticmethod
    def build_timeout_qc(msgs: Set[Timeout], sender: Id) -> TimeoutQc:
        # Convert the set of Timeout messages to a list
        msgs_list = list(msgs)

        # Extract the view and high QC from the list of messages
        view = msgs_list[0].view
        high_qc_list = [msg.high_qc for msg in msgs_list]

        # Find the highest high QC using the max function
        high_qc = max(high_qc_list, key=lambda x: x.view)

        # Extract the QC views and sender IDs
        qc_views = [msg.view for msg in msgs_list]
        sender_ids = {msg.sender for msg in msgs_list}

        # Build the TimeoutQc object
        return TimeoutQc(
            view=view,
            high_qc=high_qc,
            qc_views=qc_views,
            sender_ids=sender_ids,
            sender=sender
        )

    def update_current_view_from_timeout_qc(self, timeout_qc: TimeoutQc):
        self.current_view = timeout_qc.view + 1 if timeout_qc.view >= self.current_view else self.current_view

    def is_safe_to_timeout_invariant(self):
        # Ensure that the current view is always higher than the highest voted view or the local high QC view.
        assert self.current_view > max(self.highest_voted_view - 1,
                                       self.local_high_qc.view), "Current view should be higher than the highest voted view or local high QC view."

        # Ensure that a node waits for the timeout QC from the root committee or the last view timeout QC
        # from the previous view before changing its view.
        assert (
                self.current_view == self.local_high_qc.view + 1 or
                self.current_view == self.last_view_timeout_qc.view + 1 or
                self.current_view == self.last_view_timeout_qc.view
        ), "Node must wait for appropriate QC before changing its view."

        # If both assertions pass, the invariant is satisfied
        return True
