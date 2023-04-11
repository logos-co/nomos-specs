# The Carnot protocol is designed to be elastic, responsive, and provide fast finality
# Elastic scalability allows the protocol to operate effectively with both small and large networks
# All nodes in the Carnot network participate in the consensus of a block
# Optimistic responsiveness enables the protocol to operate quickly during periods of synchrony and honest leadership
# There is no block generation time in Carnot, allowing for fast finality
# Carnot avoids the chain reorg problem, making it compatible with PoS schemes
# This enhances the robustness of the protocol, making it a valuable addition to the ecosystem of consensus protocols


#  The protocol in Carnot operates in two modes: the happy path and the unhappy path.
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


from dataclasses import dataclass
from typing import TypeAlias, List, Set, Self, Optional, Dict, FrozenSet
from abc import abstractmethod

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
        return self.qc.block

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
        pass

    @abstractmethod
    def leader(self, view: View) -> Id:
        """
        :param view:
        :return: the leader Id of the specified view
        """
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


def is_sequential_ascending(view1: View, view2: View):
    return view1 == view2 + 1


class Carnot:
    def __init__(self, _id: Id):
        self.id: Id = _id
        # Current View counter
        self.current_view: View = 0
        # Highest voted view counter. This is used to prevent a node from voting twice or vote after timeout.
        self.highest_voted_view: View = 0
        # This is the qc from  the highest view a node has
        self.local_high_qc: Optional[Qc] = None
        # The latest view committed by a node.
        self.latest_committed_view: View = 0
        # Validated blocks with their validated QCs are included here. If commit conditions is satisfied for
        # each one of these blocks it will be committed.
        self.safe_blocks: Dict[Id, Block] = dict()
        # Block received for a specific view. Make sure the node doesn't receive duplicate blocks.
        self.seen_view_blocks: Dict[View, bool] = dict()
        # Last timeout QC and its view
        self.last_timeout_view_qc: Optional[TimeoutQc] = None
        self.last_timeout_view: Optional[View] = None
        self.overlay: Overlay = Overlay()  # TODO: integrate overlay
        # Committed blocks are kept here.
        self.committed_blocks: Dict[Id, Block] = dict()

    def block_is_safe(self, block: Block) -> bool:
        match block.qc:
            case StandardQc() as standard:
                if standard.view < self.latest_committed_view:
                    return False
                return (
                        block.view >= self.latest_committed_view and
                        is_sequential_ascending(block.view, standard.view)
                )
            case AggregateQc() as aggregated:
                if aggregated.high_qc().view < self.latest_committed_view:
                    return False
                return (
                        block.view >= self.current_view and
                        is_sequential_ascending(block.view, aggregated.view)
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

    def update_timeout_qc(self, timeout_qc: TimeoutQc):
        match (self.last_timeout_view_qc, timeout_qc):
            case (None, timeout_qc):
                self.last_timeout_view_qc = timeout_qc
            case (self.last_timeout_view_qc, timeout_qc) if timeout_qc.view > self.last_timeout_view_qc.view:
                self.last_timeout_view_qc = timeout_qc

    def receive_block(self, block: Block):
        assert block.parent() in self.safe_blocks

        if block.id() in self.safe_blocks:
            return
        if self.seen_view_blocks.get(block.view) is not None or block.view <= self.latest_committed_view:
            # TODO: Report malicious leader
            return

        if self.block_is_safe(block):
            self.safe_blocks[block.id()] = block
            self.seen_view_blocks[block.view] = True
            self.update_high_qc(block.qc)
            self.try_commit_grand_parent(block)

    def approve_block(self, block: Block, votes: Set[Vote]):
        assert block.id() in self.safe_blocks
        assert len(votes) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_child_committee(self.id, vote.voter) for vote in votes)
        assert all(vote.block == block.id() for vote in votes)
        assert block.view > self.highest_voted_view

        if (
                self.overlay.is_member_of_root_committee(self.id) and
                not self.overlay.is_member_of_leaf_committee(self.id)
        ):
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=block.view,
                qc=self.build_qc(block.view, block)
            )
            self.send(vote, self.overlay.leader(self.current_view + 1))
        else:
            vote: Vote = Vote(
                block=block.id(),
                voter=self.id,
                view=block.view,
                qc=None
            )
            if self.overlay.is_member_of_root_committee(self.id):
                self.send(vote, self.overlay.leader(block.view + 1))
            else:
                self.send(vote, *self.overlay.parent_committee(self.id))
        self.increment_voted_view(block.view)  # to avoid voting again for this view.
        self.increment_view_qc(block.qc)

    def forward_vote(self, vote: Vote):
        assert vote.block in self.safe_blocks
        assert self.overlay.is_member_of_child_committee(self.id, vote.voter)

        if self.overlay.is_member_of_root_committee(self.id):
            self.send(vote, self.overlay.leader(self.current_view + 1))

    def forward_new_view(self, msg: NewView):
        assert msg.view == self.current_view
        assert self.overlay.is_member_of_child_committee(self.id, msg.sender)

        if self.overlay.is_member_of_root_committee(self.id):
            self.send(msg, self.overlay.leader(self.current_view + 1))

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

    def propose_block(self, view: View, quorum: Quorum):
        assert self.overlay.is_leader(self.id)

        qc = None
        quorum = list(quorum)
        # happy path
        if isinstance(quorum[0], Vote):
            assert len(quorum) >= self.overlay.leader_super_majority_threshold(self.id)
            vote = quorum[0]
            qc = self.build_qc(vote.view, self.safe_blocks[vote.block], None)
        # unhappy path
        elif isinstance(quorum[0], NewView):
            assert len(quorum) >= self.overlay.leader_super_majority_threshold(self.id)
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
        self.broadcast(block)

    def is_safe_to_timeout(
            self,
    ):
        """
        Local timeout is different for the root and its child committees. If other committees timeout, they only
        stop taking part in consensus. If a member of root or its child committees timeout it sends its timeout message
        to all members of root to build the timeout qc. Using this qc we assume that the new
        overlay can be built. Hence, by building the new overlay members of root committee can send the timeout qc
        to the leaf committee of the new overlay. Upon receipt of the timeout qc the leaf committee members update
        their local_high_qc, last_timeout_view_qc and last_voted_view if the view of qcs
        (local_high_qc, last_timeout_view_qc) received is higher than their local view. Similalry last_voted_view is
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
                is_sequential_ascending(self.current_view, self.local_high_qc.view) or
                is_sequential_ascending(self.current_view, self.last_timeout_view_qc.view) or
                (self.current_view == self.last_timeout_view_qc.view)
        )

    def local_timeout(self):
        assert self.is_safe_to_timeout()

        self.increment_voted_view(self.current_view)

        if self.overlay.is_member_of_root_committee(self.id) or self.overlay.is_child_of_root_committee(self.id):
            timeout_msg: Timeout = Timeout(
                view=self.current_view,
                high_qc=self.local_high_qc,
                # local_timeout is only true for the root committee or members of its children
                # root committee or its children can trigger the timeout.
                timeout_qc=self.last_timeout_view_qc,
                sender=self.id
            )
            self.send(timeout_msg, *self.overlay.root_committee())

    def timeout_detected(self, msgs: Set[Timeout]):
        """
        Root committee detected that supermajority of root + its children has timed out
        The view has failed and this information is sent to all participants along with the information
        necessary to reconstruct the new overlay
        """
        assert len(msgs) == self.overlay.leader_super_majority_threshold(self.id)
        # The checks below  are performed in is_safe_to_timeout().
        # assert all(msg.view >= self.current_view for msg in msgs)
        # assert self.current_view > max(self.highest_voted_view - 1, self.local_high_qc.view)
        assert len(set(msg.view for msg in msgs)) == 1
        assert self.overlay.is_member_of_root_committee(self.id)

        timeout_qc = self.build_timeout_qc(msgs, self.id)
        self.update_timeout_qc(timeout_qc)
        self.update_high_qc(timeout_qc.high_qc)
        # The view failed and the node timeout. The node cannot timeout itself again until it gets updated
        # from a higher qc, either from a TimeoutQc or from a Qc coming from a newer proposed block.
        # In case the node do not get updated because the received qc is not new enough we need to skip
        # rebuilding the overlay and broadcasting our own qc
        if not self.is_safe_to_timeout():
            return
        self.rebuild_overlay_from_timeout_qc(timeout_qc)
        self.broadcast(timeout_qc)  # we broadcast so all nodes can get ready for voting on a new view

    def approve_new_view(self, new_views: Set[NewView]):
        assert not self.overlay.is_member_of_leaf_committee(self.id)
        assert len(set(new_view.view for new_view in new_views)) == 1
        # newView.view == self.last_timeout_view_qc.view for member of root committee and its children because
        # they have already created the timeout_qc. For other nodes newView.view > self.last_timeout_view_qc.view.
        if self.last_timeout_view_qc is not None:
            assert all(new_view.view >= self.last_timeout_view_qc.view for new_view in new_views)
        assert all(new_view.view == new_view.timeout_qc.view for new_view in new_views)
        assert len(new_views) == self.overlay.super_majority_threshold(self.id)
        assert all(self.overlay.is_member_of_child_committee(self.id, new_view.sender) for new_view in new_views)

        new_views = list(new_views)
        timeout_qc = new_views[0].timeout_qc
        new_high_qc = timeout_qc.high_qc

        self.rebuild_overlay_from_timeout_qc(timeout_qc)

        if new_high_qc.view < self.local_high_qc.view:
            return

        self.update_high_qc(new_high_qc)
        self.update_timeout_qc(timeout_qc)
        # The view failed and the node timeout. The node cannot timeout itself again until it gets updated
        # from a higher qc, either from a TimeoutQc or from a Qc coming from a newer proposed block.
        # In case the node do not get updated because the received qc is not new enough we need to skip
        # rebuilding the overlay and broadcasting our own qc
        if not self.is_safe_to_timeout():
            return

        if self.overlay.is_member_of_root_committee(self.id):
            timeout_msg = NewView(
                view=self.current_view,
                high_qc=self.local_high_qc,
                sender=self.id,
                timeout_qc=timeout_qc,
            )
            self.send(timeout_msg, self.overlay.leader(self.current_view + 1))
        else:
            timeout_msg = NewView(
                view=self.current_view,
                high_qc=self.local_high_qc,
                sender=self.id,
                timeout_qc=timeout_qc,
            )
            self.send(timeout_msg, *self.overlay.parent_committee(self.id))
        self.increment_view_timeout_qc(timeout_qc)
        # This checks if a node has already incremented its voted view by local_timeout. If not then it should
        # do it now to avoid voting in this view.
        if self.highest_voted_view < self.current_view:
            self.increment_voted_view(timeout_qc.view)

    # Just a suggestion that received_timeout_qc can be reused by each node when the process timeout_qc of the NewView msg.
    def received_timeout_qc(self, timeout_qc: TimeoutQc):
        # assert timeout_qc.view >= self.current_view
        new_high_qc = timeout_qc.high_qc
        if new_high_qc.view > self.local_high_qc.view:
            self.update_high_qc(new_high_qc)
            self.update_timeout_qc(timeout_qc)
        if not self.is_safe_to_timeout():
            return
        self.rebuild_overlay_from_timeout_qc(timeout_qc)
        if self.overlay.is_member_of_leaf_committee(self.id):
            timeout_msg = NewView(
                view=self.current_view,
                high_qc=self.local_high_qc,
                sender=self.id,
                timeout_qc=timeout_qc,
            )
            self.send(timeout_msg, *self.overlay.parent_committee(self.id))
            # This checks if a node has already incremented its voted view by local_timeout. If not then it should
            # do it now to avoid voting in this view.
            if self.highest_voted_view < self.current_view:
                self.increment_voted_view(timeout_qc.view)

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

    def send(self, vote: Vote | Timeout | NewView | TimeoutQc, *ids: Id):
        pass

    def broadcast(self, block):
        pass

    # todo blocks from latest_committed_block to grand_parent must be committed.
    def try_commit_grand_parent(self, block: Block):

        parent = self.safe_blocks.get(block.parent())
        grand_parent = self.safe_blocks.get(parent.parent())
        while grand_parent and grand_parent.view > self.latest_committed_view:
            # this case should just trigger on genesis_case,
            # as the preconditions on outer calls should check on block validity
            if not parent or not grand_parent:
                return
            can_commit = (
                    parent.view == (grand_parent.view + 1) and
                    isinstance(block.qc, (StandardQc,)) and
                    isinstance(parent.qc, (StandardQc,))
            )
            if can_commit:
                self.committed_blocks[grand_parent.id()] = grand_parent
                self.increment_latest_committed_view(grand_parent.view)
            grand_parent = self.safe_blocks.get(grand_parent.parent())

    def increment_voted_view(self, view: View):
        self.highest_voted_view = max(view, self.highest_voted_view)

    def increment_latest_committed_view(self, view: View):
        self.latest_committed_view = max(view, self.latest_committed_view)

    def increment_view_qc(self, qc: Qc):
        if qc.view < self.current_view:
            return
        self.last_timeout_view_qc = None
        self.current_view = qc.view + 1

    def increment_view_timeout_qc(self, timeout_qc: TimeoutQc):
        if timeout_qc is None or timeout_qc.view < self.current_view:
            return
        self.last_timeout_view_qc = timeout_qc
        self.current_view = self.last_timeout_view_qc.view + 1
        return True

    @staticmethod
    def get_max_timeout(timeouts: Set[Timeout]) -> Timeout:
        assert len(timeouts) > 0
        return max(timeouts, key=lambda time: time.qc.view)


if __name__ == "__main__":
    pass
