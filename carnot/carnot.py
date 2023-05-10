# The Carnot protocol is designed to be elastic, responsive, and provide fast finality
# Elastic scalability allows the protocol to operate effectively with both small and large networks
# All nodes in the Carnot network participate in the consensus of a block
# Optimistic responsiveness enables the protocol to operate quickly during periods of synchrony and honest leadership
# There is no block generation time in Carnot, allowing for fast finality
# Carnot avoids the chain reorg problem, making it compatible with PoS schemes
# This enhances the robustness of the protocol, making it a valuable addition to the ecosystem of consensus protocols


# The protocol in Carnot operates in two modes: the happy path and the unhappy path.
#
# In Carnot, nodes are arranged in a binary tree overlay committee structure. Moreover, Carnot is a
# pipelined consensus protocol where a block contains the proof of attestation of its parent. In happy path the
# leader proposes a block that contains a quorum certificate (QC) with votes from more than two-thirds of the root
# committee and its child committee/ committees. The voting process begins at the leaf committee where nodes verify
# the proposal and send their votes to the parent committee. Once a node in the parent committee receives more than
# two-thirds of the votes from its child committee members, it sends its votes to its parent. This process continues
# recursively until the root committee members collect votes from its child committee/ committees. The root committee
# member builds a QC from the votes and sends it to the next leader. The leader builds a QC and proposes the next block
# upon receiving more than two-thirds of votes.


# In the unhappy path, if a node does not receive a message within a timeout interval, it will timeout. Only nodes at
# the root committee and its child committee/ committees send their timeout messages to the root committee. The root
# committee builds a timeout QC from more than two-thirds of messages, recalculates the new overlay, and broadcasts it
# to the network. Similar to the happy path, the timeout message moves from leaves to the root. Each parent waits for
# more than two-thirds of timeout messages from its child committees and sends its timeout to the parent committee once
# the threshold is reached. A node in the root committee builds a QC from timeout messages received from its
# child committee/committees and forwards it to the next leader. Upon receiving more than two-thirds of timeout
# messages, the next leader builds an aggregated QC and proposes the next block containing the aggregated QC.
# It should be noted that while receiving timeout messages, each node also updates its high_qc (the most recent QC)
# and passes it to its parent through the timeout message. In this way, the aggregated QC will include the high_qc seen
# by the majority of honest nodes. Hence, after the view change, the protocol safety is preserved.


# Please note this is still a work in progress

from dataclasses import dataclass
from typing import TypeAlias, List, Set, Self, Optional, Dict
from abc import abstractmethod, ABC

Id: TypeAlias = bytes
View: TypeAlias = int
Committee: TypeAlias = Set[Id]


def int_to_id(i: int) -> Id:
    return bytes(str(i), encoding="utf8")


@dataclass(unsafe_hash=True)
class StandardQc:
    block: Id
    view: View

    def view(self) -> View:
        return self.view


@dataclass
class AggregateQc:
    qcs: List[View]
    highest_qc: StandardQc
    view: View

    def view(self) -> View:
        return self.view

    def high_qc(self) -> StandardQc:
        assert self.highest_qc.view == max(self.qcs)
        return self.highest_qc


Qc: TypeAlias = StandardQc | AggregateQc


@dataclass
class Block:
    view: View
    qc: Qc
    _id: Id  # this is an abstration over the block id, which should be the hash of the contents

    def extends(self, ancestor: Self) -> bool:
        """
        :param ancestor:
        :return: true if block is descendant of the ancestor in the chain
        """
        return self.view > ancestor.view

    def parent(self) -> Id:
        match self.qc:
            case StandardQc(block):
                return block
            case AggregateQc() as aqc:
                return aqc.high_qc().block

    def id(self) -> Id:
        return self._id


@dataclass(unsafe_hash=True)
class Vote:
    block: Id
    view: View
    voter: Id
    qc: Optional[Qc]


@dataclass
class TimeoutQc:
    view: View
    high_qc: Qc
    qc_views: List[View]
    sender_ids: Set[Id]
    sender: Id


@dataclass
class Timeout:
    """
    Local timeout field is only used by the root committee and its children when they timeout. The timeout_qc is built
    from local_timeouts. Leaf nodes when receive timeout_qc build their timeout msg and includes the timeout_qc in it.
    The timeout_qc is indicator that the root committee and its child committees (if exist) have failed to collect votes.
    """
    view: View
    high_qc: Qc
    sender: Id
    timeout_qc: TimeoutQc


# Timeout has been detected, nodes agree on it and gather high qc
@dataclass
class NewView:
    view: View
    high_qc: Qc
    sender: Id
    timeout_qc: TimeoutQc


Quorum: TypeAlias = Set[Vote] | Set[NewView]


Payload: TypeAlias = Block | Vote | Timeout | NewView | TimeoutQc

@dataclass
class BroadCast:
    payload: Payload


@dataclass
class Send:
    to: [Id]
    payload: Payload


Event: TypeAlias = BroadCast | Send


class Overlay:
    """
    Overlay structure for a View
    """

    @abstractmethod
    def is_leader(self, _id: Id):
        """
        :param _id:  Node id to be checked
        :return: true if node is the leader of the current view
        """
        return _id == self.leader()

    @abstractmethod
    def leader(self) -> Id:
        """
        :param view:
        :return: the leader Id of the specified view
        """
        pass

    @abstractmethod
    def next_leader(self) -> Id:
        pass

    @abstractmethod
    def is_member_of_leaf_committee(self, _id: Id) -> bool:
        """
        :param _id: Node id to be checked
        :return: true if the participant with Id _id is in the leaf committee of the committee overlay
        """
        pass

    @abstractmethod
    def is_member_of_root_committee(self, _id: Id) -> bool:
        """
        :param _id:
        :return: true if the participant with Id _id is member of the root committee withing the tree overlay
        """
        pass

    @abstractmethod
    def is_member_of_child_committee(self, parent: Id, child: Id) -> bool:
        """
        :param parent:
        :param child:
        :return: true if participant with Id child is member of the child committee of the participant with Id parent
        """
        pass

    @abstractmethod
    def parent_committee(self, _id: Id) -> Optional[Committee]:
        """
        :param _id:
        :return: Some(parent committee) of the participant with Id _id withing the committee tree overlay
        or Empty if the member with Id _id is a participant of the root committee
        """
        pass

    @abstractmethod
    def leaf_committees(self) -> Set[Committee]:
        pass

    @abstractmethod
    def root_committee(self) -> Committee:
        """
        :return: returns root committee
        """
        pass

    @abstractmethod
    def is_child_of_root_committee(self, _id: Id) -> bool:
        """
        :return: returns child committee/s of root committee if present
        """
        pass

    @abstractmethod
    def leader_super_majority_threshold(self, _id: Id) -> int:
        """
        Amount of distinct number of messages for a node with Id _id member of a committee
        The return value may change depending on which committee the node is member of, including the leader
        :return:
        """
        pass

    @abstractmethod
    def super_majority_threshold(self, _id: Id) -> int:
        pass


def download(view) -> Block:
    raise NotImplementedError


class Carnot:
    def __init__(self, _id: Id):
        self.id: Id = _id
        # Current View counter
        # It is the view currently being processed by the node. Once a Qc is received, the view is considered completed
        # and the current view is updated to qc.view+1
        self.current_view: View = 0
        # Highest voted view counter. This is used to prevent a node from voting twice or vote after timeout.
        self.highest_voted_view: View = -1
        # This is most recent (in terms of view) Standard QC that has been received by the node
        self.local_high_qc: Optional[Qc] = None
        # Validated blocks with their validated QCs are included here. If commit conditions are satisfied for
        # each one of these blocks it will be committed.
        self.safe_blocks: Dict[Id, Block] = dict()
        # Whether the node time out in the last view and corresponding qc
        self.last_view_timeout_qc: Optional[TimeoutQc] = None
        self.overlay: Overlay = Overlay()  # TODO: integrate overlay


    # Committing conditions for a block
    # TODO: explain the conditions in comment
    def can_commit_grandparent(self, block) -> bool:
        parent = self.safe_blocks.get(block.parent())
        grand_parent = self.safe_blocks.get(parent.parent())
        # this case should just trigger on genesis_case,
        # as the preconditions on outer calls should check on block validity
        if not parent or not grand_parent:
            return False
        return (
            parent.view == (grand_parent.view + 1) and
            isinstance(block.qc, (StandardQc,)) and
            isinstance(parent.qc, (StandardQc,))
        )


    # The latest committed view is implicit in the safe blocks tree given
    # the committing conditions.
    # For convenience, this is an helper method to retrieve that value.
    def latest_committed_view(self) -> View:
        return self.latest_committed_block().view

    # Return the list of blocks received by a node for a specific view.
    # It will return more than one block only in case of a malicious leader
    def blocks_in_view(self, view: View) -> List[Block]:
        return [block for block in self.safe_blocks.values() if block.view == view]

    def genesis_block(self) -> Block:
        return self.blocks_in_view(0)[0]

    def latest_committed_block(self) -> Block:
        for view in range(self.current_view, 0, -1):
            for block in self.blocks_in_view(view):
                if self.can_commit_grandparent(block):
                    return self.safe_blocks.get(self.safe_blocks.get(block.parent()).parent())
        # genesis blocks is always considered committed
        return self.genesis_block()

    # Given committing conditions, the set of committed blocks is implicit
    # in the safe blocks tree. For convenience, this is an helper method to
    # retrieve that set.
    def committed_blocks(self) -> Dict[Id, Block]:
        tip = self.latest_committed_block()
        committed_blocks = {tip.id(): tip, self.genesis_block().id: self.genesis_block()}
        while tip.view > 0:
            committed_blocks[tip.id()] = tip
            tip = self.safe_blocks.get(tip.parent())
        return committed_blocks

    def block_is_safe(self, block: Block) -> bool:
        return (
            block.view >= self.current_view and
            block.view == block.qc.view + 1
        )

    # Ask Dani
    def update_high_qc(self, qc: Qc):
        match (self.local_high_qc, qc):
            case (None, StandardQc() as new_qc):
                self.local_high_qc = new_qc
            case (None, AggregateQc() as new_qc):
                self.local_high_qc = new_qc.high_qc()
            case (old_qc, StandardQc() as new_qc) if new_qc.view > old_qc.view:
                self.local_high_qc = new_qc
            case (old_qc, AggregateQc() as new_qc) if new_qc.high_qc().view != old_qc.view:
                self.local_high_qc = new_qc.high_qc()
        # if my view is not updated I update it when I see a qc for that view
        if qc.view == self.current_view:
            self.current_view = self.current_view + 1

    def update_timeout_qc(self, timeout_qc: TimeoutQc):
        match (self.last_view_timeout_qc, timeout_qc):
            case (None, timeout_qc):
                self.last_view_timeout_qc = timeout_qc
            case (self.last_view_timeout_qc, timeout_qc) if timeout_qc.view > self.last_view_timeout_qc.view:
                self.last_view_timeout_qc = timeout_qc

    def receive_block(self, block: Block):
        assert block.parent() in self.safe_blocks

        if block.id() in self.safe_blocks:
            return
        if self.blocks_in_view(block.view) != [] or block.view <= self.latest_committed_view():
            # TODO: Report malicious leader
            # TODO: it could be possible that a malicious leader send a block to a node and another one to
            # the rest of the network. The node should be able to catch up with the rest of the network after having
            # validated that the history of the block is correct and diverged from its fork.
            # By rejecting any other blocks except the first one received for a view this code does NOT do that.
            return

        # TODO: check the proposer of the block is indeed leader for that view

        if self.block_is_safe(block):
            self.safe_blocks[block.id()] = block
            self.update_high_qc(block.qc)

    def approve_block(self, block: Block, votes: Set[Vote]) -> Event:
        assert block.id() in self.safe_blocks
        assert len(votes) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_child_committee(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)
        assert self.highest_voted_view < block.view

        if self.overlay.is_member_of_root_committee(self.id):
            qc = self.build_qc(block.view, block, None)
        else:
            qc = None

        vote: Vote = Vote(
            block=block.id(),
            voter=self.id,
            view=block.view,
            qc=qc
        )

        self.highest_voted_view = max(self.highest_voted_view, block.view)

        if self.overlay.is_member_of_root_committee(self.id):
            return Send(to=self.overlay.leader(block.view + 1), payload=vote)
        return Send(to=self.overlay.parent_committee(self.id), payload=vote)

    def forward_vote(self, vote: Vote) -> Optional[Event]:
        assert vote.block in self.safe_blocks
        assert self.overlay.is_member_of_child_committee(self.id, vote.voter)
        # we only forward votes after we've voted ourselves
        assert self.highest_voted_view == vote.view

        if self.overlay.is_member_of_root_committee(self.id):
            return Send(to=self.overlay.next_leader(), payload=vote)

    def forward_new_view(self, msg: NewView) -> Optional[Event]:
        assert msg.view == self.current_view
        assert self.overlay.is_member_of_child_committee(self.id, msg.sender)
        # we only forward votes after we've voted ourselves
        assert self.highest_voted_view == msg.view

        if self.overlay.is_member_of_root_committee(self.id):
            return Send(to=self.overlay.next_leader(), payload=msg)

    def build_qc(self, view: View, block: Optional[Block], new_views: Optional[Set[NewView]]) -> Qc:
        # unhappy path
        if new_views:
            new_views = list(new_views)
            return AggregateQc(
                qcs=[msg.high_qc.view for msg in new_views],
                highest_qc=max(new_views, key=lambda x: x.high_qc.view).high_qc,
                view=new_views[0].view
            )
        # happy path
        return StandardQc(
            view=view,
            block=block.id()
        )

    def propose_block(self, view: View, quorum: Quorum) -> Event:
        assert self.overlay.is_leader(self.id)
        assert len(quorum) >= self.overlay.leader_super_majority_threshold(self.id)

        qc = None
        quorum = list(quorum)
        # happy path
        if isinstance(quorum[0], Vote):
            vote = quorum[0]
            qc = self.build_qc(vote.view, self.safe_blocks[vote.block], None)
        # unhappy path
        elif isinstance(quorum[0], NewView):
            new_view = quorum[0]
            qc = self.build_qc(new_view.view, None, quorum)

        block = Block(
            view=view,
            qc=qc,
            # Dummy id for proposing next block
            _id=int_to_id(hash(
                (
                    bytes(f"{view}".encode(encoding="utf8")),
                    bytes(f"{qc.view}".encode(encoding="utf8"))
                )
            ))
        )
        return BroadCast(payload=block)

    def is_safe_to_timeout_invariant(
            self,
    ):
        """
        Local timeout is different for the root and its child committees. If other committees timeout, they only
        stop taking part in consensus. If a member of root or its child committees timeout it sends its timeout message
        to all members of root to build the timeout qc. Using this qc we assume that the new
        overlay can be built. Hence, by building the new overlay members of root committee can send the timeout qc
        to the leaf committee of the new overlay. Upon receipt of the timeout qc the leaf committee members update
        their local_high_qc, last_timeout_view_qc and last_voted_view if the view of qcs
        (local_high_qc, last_timeout_view_qc) received is higher than their local view. Similarly last_voted_view is
        updated if it is greater than the current last_voted_view. When parent committee member receives more than two
        third of timeout messages from its children it also updates its local_high_qc, last_timeout_view_qc and
        last_voted_view if needed and then send its timeout message upward. In this way the latest qcs move upward
        that makes it possible for the next leader to propose a block with the latest local_high_qcs in aggregated qc
        from more than two third members of root committee and its children.
        """

        # Make sure the node doesn't time out continuously without finishing the step to increment the current view.
        # Make sure current view is always higher than the local_high_qc so that the node won't timeout unnecessary
        # for a previous view.
        assert self.current_view > max(self.highest_voted_view - 1, self.local_high_qc.view)
        # This condition makes sure a node waits for timeout_qc from root committee to change increment its view with
        # a view change.
        # A node must  change its view  after making sure it has the high_Qc or last_timeout_view_qc
        # from previous view.
        return (
                self.current_view == self.local_high_qc.view + 1 or
                self.current_view == self.last_view_timeout_qc.view + 1 or
                (self.current_view == self.last_view_timeout_qc.view)
        )

    def local_timeout(self) -> Optional[Event]:
        """
        Root committee changes for each failure, so repeated failure will be handled by different
        root committees
        """
        # avoid voting after we timeout
        self.highest_voted_view = self.current_view

        if self.overlay.is_member_of_root_committee(self.id) or self.overlay.is_child_of_root_committee(self.id):
            timeout_msg: Timeout = Timeout(
                view=self.current_view,
                high_qc=self.local_high_qc,
                # local_timeout is only true for the root committee or members of its children
                # root committee or its children can trigger the timeout.
                timeout_qc=self.last_view_timeout_qc,
                sender=self.id
            )
            return Send(payload=timeout_msg, to=self.overlay.root_committee())

    def timeout_detected(self, msgs: Set[Timeout]) -> Event:
        """
        Root committee detected that supermajority of root + its children has timed out
        The view has failed and this information is sent to all participants along with the information
        necessary to reconstruct the new overlay

        """
        assert len(msgs) == self.overlay.leader_super_majority_threshold(self.id)
        assert all(msg.view >= self.current_view for msg in msgs)
        assert len(set(msg.view for msg in msgs)) == 1
        assert self.overlay.is_member_of_root_committee(self.id)

        timeout_qc = self.build_timeout_qc(msgs, self.id)
        return BroadCast(payload=timeout_qc)  # we broadcast so all nodes can get ready for voting on a new view
        # Note that receive_timeout qc should be called for root nodes as well

    # noinspection PyTypeChecker
    def approve_new_view(self, timeout_qc: TimeoutQc, new_views: Set[NewView]) -> Event:
        """
        We will always need for timeout_qc to have been preprocessed by the received_timeout_qc method when the event
        happens before approve_new_view is processed.
        """
        # newView.view == self.last_timeout_view_qc.view for member of root committee and its children because
        # they have already created the timeout_qc. For other nodes newView.view > self.last_timeout_view_qc.view.
        if self.last_view_timeout_qc is not None:
            assert all(new_view.view > self.last_view_timeout_qc.view for new_view in new_views)
        assert all(new_view.timeout_qc.view == timeout_qc.view for new_view in new_views)
        assert len(new_views) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_child_committee(self.id, new_view.sender) for new_view in new_views)
        # the new view should be for the view successive to the timeout
        assert all(timeout_qc.view + 1 == new_view.view for new_view in new_views)
        view = timeout_qc.view + 1
        assert self.highest_voted_view < view

        # get the highest qc from the new views
        messages_high_qc = (new_view.high_qc for new_view in new_views)
        high_qc = max(
            [timeout_qc.high_qc, *messages_high_qc],
            key=lambda qc: qc.view
        )
        self.update_high_qc(high_qc)
        timeout_msg = NewView(
            view=view,
            # TODO: even if this event is processed "later", we should not allow high_qc.view to be >= timeout_qc.view
            high_qc=self.local_high_qc,
            sender=self.id,
            timeout_qc=timeout_qc,
        )

        # This checks if a node has already incremented its voted view by local_timeout. If not then it should
        # do it now to avoid voting in this view.
        self.highest_voted_view = max(self.highest_voted_view, view)

        if self.overlay.is_member_of_root_committee(self.id):
            return Send(payload=timeout_msg, to=[self.overlay.next_leader()])
        return Send(payload=timeout_msg, to=self.overlay.parent_committee(self.id))



    # Just a suggestion that received_timeout_qc can be reused by each node when the process timeout_qc of the NewView msg.
    # TODO: check that receiving (and processing) a timeout qc "in the future" allows to process old(er) blocks
    # e.g. we might still need access to the old leader schedule to validate qcs
    def receive_timeout_qc(self, timeout_qc: TimeoutQc):
        if timeout_qc.view < self.current_view:
            return
        new_high_qc = timeout_qc.high_qc
        self.update_high_qc(new_high_qc)
        self.update_timeout_qc(timeout_qc)
        # Update our current view and go ahead with the next step
        self.update_current_view_from_timeout_qc(timeout_qc)
        self.rebuild_overlay_from_timeout_qc(timeout_qc)

    def rebuild_overlay_from_timeout_qc(self, timeout_qc: TimeoutQc):
        assert timeout_qc.view >= self.current_view
        self.overlay = Overlay()

    @staticmethod
    def build_timeout_qc(msgs: Set[Timeout], sender: Id) -> TimeoutQc:
        msgs = list(msgs)
        return TimeoutQc(
            view=msgs[0].view,
            high_qc=max(msgs, key=lambda x: x.high_qc.view).high_qc,
            qc_views=[msg.view for msg in msgs],
            sender_ids={msg.sender for msg in msgs},
            sender=sender,
        )

    def update_current_view_from_timeout_qc(self, timeout_qc: TimeoutQc):
        self.current_view = timeout_qc.view + 1


if __name__ == "__main__":
    pass
