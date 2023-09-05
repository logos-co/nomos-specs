# Background / Rationale / Motivation

 The Carnot protocol is designed to be elastic, responsive, and provide fast finality
 Elastic scalability allows the protocol to operate effectively with both small and large networks
 All nodes in the Carnot network participate in the consensus of a block
 Optimistic responsiveness enables the protocol to operate quickly during periods of synchrony and honest leadership
 There is no block generation time in Carnot, allowing for fast finality
 Carnot avoids the chain reorg problem, making it compatible with PoS schemes
 This enhances the robustness of the protocol, making it a valuable addition to the ecosystem of consensus protocols

# The Protocol
 The protocol in Carnot operates in two modes: the happy path and the unhappy path.

 In Carnot, nodes are arranged in a binary tree overlay committee structure. Moreover, Carnot is a
 pipelined consensus protocol where a block contains the proof of attestation of its parent. In happy path the
 leader proposes a block that contains a quorum certificate (QC) with votes from more than two-thirds of the root
 committee and its child committee/ committees. The voting process begins at the leaf committee where nodes verify
 the proposal and send their votes to the parent committee. Once a node in the parent committee receives more than
 two-thirds of the votes from its child committee members, it sends its votes to its parent. This process continues
 recursively until the root committee members collect votes from its child committee/ committees. The root committee
 member builds a QC from the votes and sends it to the next leader. The leader builds a QC and proposes the next block
 upon receiving more than two-thirds of votes.


 In the unhappy path, if a node does not receive a message within a timeout interval, it will timeout. Only nodes at
 the root committee and its child committee/ committees send their timeout messages to the root committee. The root
 committee builds a timeout QC from more than two-thirds of messages, recalculates the new overlay, and broadcasts it
 to the network. Similar to the happy path, the timeout message moves from leaves to the root. Each parent waits for
 more than two-thirds of timeout messages from its child committees and sends its timeout to the parent committee once
 the threshold is reached. A node in the root committee builds a QC from timeout messages received from its
 child committee/committees and forwards it to the next leader. Upon receiving more than two-thirds of timeout
 messages, the next leader builds an aggregated QC and proposes the next block containing the aggregated QC.
 It should be noted that while receiving timeout messages, each node also updates its high_qc (the most recent QC)
 and passes it to its parent through the timeout message. In this way, the aggregated QC will include the high_qc seen
 by the majority of honest nodes. Hence, after the view change, the protocol safety is preserved.

# Carnot Specification
This is the pseudocode specification of the Carnot consensus algorithm.
In this specification we will omit any cryptographic material, block validity and proof checks. A real implementation is expected to check those before hitting this code.
In addition, all types can be expected to have their invariants checked by the type contract, e.g. in an instance of type `Qc::Aggregate` the `high_qc` field is always the most recent qc among the aggregate qcs and the code can skip this check.

'Q:' is used to indicate unresolved questions.
Notation is loosely based on CDDL.

Similar to the Carnot algorithm, this specification will be event-based, prescribing the actions to perform in response to relevant events in the Carnot consensus.
Events should be processed one at a time, picking any from the available ones.
As for ordering between events, there are some constraints (e.g. can't process a proposal before it's parent) which will likely form a DAG of relations. The expectation is that an implementation will respect these requirements by processing only events which have all preconditions satisfied.

## Messages
A critical piece in the protocol, these are the different kind of messages used by participants during the protocol execution.
* `Block`: propose a new block
* `Vote`: vote for a block proposal
* `Timeout`: propose to jump to a new view after a proposal for the current one was not received before a configurable timeout.


### Block

(sometimes also called proposal)
We assume an unique identifier of the block can be obtained, for example by hashing its contents. We will use the `id()` function to access the identifier of the current block.
We also assume that a unique tree order of blocks can be determined, and in particular each participant can identify the parent of each block. We will use the `parent()` function to access such parent block.
        
```python
@dataclass
class Block:
    view: View
    qc: Qc
```

##### View

A monotonically increasing number (considerations about the size?)

```python
View = int
```

##### Qc

There are currently two different types of QC:
```python
Qc = StandardQc | AggregateQc
```

###### Standard

Q: there can only be one block on which consensus in achieved for a view, so maybe the block field is redundant?

```python
class StandardQc:
    view: View
    block: Id
```

###### Aggregate

`high_qc` is `Qc` for the most recent view among the aggregated ones. The rest of the qcs are ignored in the rest of this algorithm. 

We assume there is a  `block` function available that returns the block for the Qc. In case of a standard qc, this is trivially qc.block, while for aggregate it can be obtained by accessing `high_qc`. `high_qc` is guaranteed to be a 'Standard' qc.

```python
class AggregateQc:
    view: View
    qcs: List[Qc]

    def high_qc(self) -> Qc:
        return max(self.qcs, key=lambda qc: qc.view)
```

##### Id
undef, will assume a 32-byte opaque string

```python
Id: bytes = bytearray(32)
```

### Vote

A vote for `block` in `view`
qc is the optional field containing the QC built by root nodes from 2/3 + 1 votes from their child committees and forwarded the the next view leader.

```python
class Vote:
    block: Id
    view: View
    voter: Id
    qc: Option[Qc]
```

### Timeout

```python
class Timeout:
    view: View
    high_qc: AggregateQc
```
## Local Variables
Participants in the protocol are expected to mainting the following data in addition to the DAG of received proposal:
* `current_view`
* `local_high_qc`
* `latest_committed_view`
* `collection`: TODO rename

```python
CURRENT_VIEW: View
LOCAL_HIGH_QC: Qc
LATEST_COMMITTED_VIEW: View
SAFE_BLOCKS: Set[Block]
LAST_VIEW_TIMEOUT_QC: TimeoutQc
```


## Available Functions
The following functions are expected to be available to participants during the execution of the protocol:
* `leader(view)`: returns the leader of the view.
* `reset_timer()`: resets timer. If the timer expires the `timeout` routine is triggered.
* `extends(block, ancestor)`: returns true if block is descendant of the ancestor in the chain.

* `download(view)`: Download missing block for the view.
     getMaxViewQC(qcs): returns the qc with the highest view number.
* `member_of_leaf_committee()`: returns true if the participant executing the function is in the leaf committee of the committee overlay.

* `member_of_root_com()`: returns true if the participant executing the function is member of the root committee withing the tree overlay.

* `member_of_internal_com()`: returns truee if the participant executing the function is member of internal committees within the committee tree overlay

* `child_committee(participant)`: returns true if the participant passed as argument is member of the child committee of the participant executing the function.

* `supermajority(votes)`: the behavior changes with the position of a participant in the overlay:
    * Root committee: returns if the number of distinctive signers of votes for a block in the child committee is equal to the threshold.

* `leader_supermajority(votes)`: returns if the number of distinct voters for a block is 2/3 + 1 for both children committees of root committee and overall 2/3 + 1

* `morethanSsupermajority(votes)`: returns if the number of distinctive signers of votes for a block is is more than the threshold: TODO
* `parent_committe`: return the parent committee of the participant executing the function withing the committee tree overlay. Result is undefined if called from a participant in the root committee.


<!-- #####Supermajority of child votes is 2/3 +1 votes from members of child committees
#####Supermajority for the qc to be included in the block, should have at least 2/3+1 votes from both children of the root committee and overal 2/3 +1
#####combined votes of the root committee+its child committees. -->



## Core events

These are the core events necessary for the Carnot consensus protocol. In response to such events a participant is expected to execute the corresponding handler action.

* receive block b -> `receive_block(b)`
    Preconditions:
    * `b.parent() in SAFE_BLOCKS`
* receive a supermajority of votes for block b -> `vote(b, votes)`
    Preconditions:
    * `b in SAFE_BLOCKS`
    * `local_timeout(b.view)` never called
* receive a vote v for block b when a supermajority of votes already exists -> `forward_votes(b, v)`
    Preconditions:
    * `b in SAFE_BLOCKS`
    * `vote(b, some_votes)` already called and `v not in some_votes`
    * `local_timeout(b.view)` never called
* `current_time() - time(last view update) > TIMEOUT` and received new overlay -> `local_timeout(last view, new_overlay)`
* leader for view v and leader supermajority for previous proposal -> `propose_block(v, votes)`
* receive a supermajority of timeouts for view v -> `timeout(v, timeouts)`
    Preconditions:
    * `local_timeout(v)` already called


### Receive block

```python3
def receive_block(block: Block):
    # checking preconditions
    assert block.parent() in SAFE_BLOCKS

    if block.id() in SAFE_BLOCKS or block.view <= LATEST_COMMITTED_VIEW:
        return
        
    if safe_block(block):
        SAFE_BLOCKS.add(block)
        update_high_qc(block.qc)
```
##### Auxiliary functions

```python
def safe_block(block: Block):
    match block.qc:
        case StandardQc() as standard:
            # Previous leader did not fail and its proposal was certified
            if standard.view <= LATEST_COMMITED_BLOCK:
                return False
            # this check makes sure block is not old 
            # and the previous leader did not fail
            return block.view >= LATEST_COMMITED_BLOCK and block.view == (standard.view + 1)        
        
        case AggregateQc() as aggregated_qc:
            # Verification of block.aggQC.highQC along 
            # with signature or block.aggQC.signature is sufficient.
            # No need to verify each qc inside block.aggQC
            if aggregated_qc.high_qc().view <= LATEST_COMMITED_BLOCK:
                return False
            return block.view >= CURRENT_VIEW
            # we ensure by construction this extends the block in
            # high_qc since that is by definition the parent of this block
```

```python
# FIX_ME: Don't think we need to specify this as a function if we don't use
# LAST_COMMITTED_VIEW
# Commit a grand parent if the grandparent and 
# the parent have been added during two consecutive views.
def try_to_commit_grand_parent(block: Block):
    parent = block.parent()
    grand_parent = parent.parent()
    return (
            parent.view == (grand_parent.view + 1) and
            isinstance(block.qc, (StandardQc, )) and # Q: Is this necessary?
            isinstance(parent.qc, (StandardQc, )) # Q: Is this necessary?
    )
    # Update last_committed_view ?
```

```python
# Update the latest certification (qc)
def update_high_qc(qc: Qc):
    match qc:
        # Happy case
        case Standard() as qc:
            # TODO: revise
            if qc.view > LOCAL_HIGH_QC.view:
                LOCAL_HIGH_QC = qc
            # Q: The original pseudocde checked for possilbly
            # missing view and downloaded them, but I think
            # we already dealt with this in receive_block
        # Unhappy case
        case Aggregate() as qc:
            high_qc = qc.high_qc()
            if high_qc.view != LOCAL_HIGH_QC.view:
                LOCAL_HIGH_QC = high_qc
                # Q: same thing about missing views
```

### Vote

```python
def vote(block: Block, votes: Set[Vote]):
    # check preconditions
    assert block in SAFE_BLOCKS
    assert supermajority(votes)
    assert all(child_committee(vote.id) for vote in votes)
    assert all(vote.block == block for vote in votes)

    vote = create_vote(votes)

    if member_of_root():
        vote.qc = build_qc(votes)
        send(vote, leader(CURRENT_VIEW + 1))
    else:
        send(vote, parent_committee())
    
    # Q: what about a node that is joining later and does not
    # have access to votes? how does it commit blocks?
    current_view += 1
    reset_timer()
    try_to_commit_grandparent(block)
```


### Forward vote
```python
def forward_vote(vote: Vote):
    assert vote.block in SAFE_BLOCKS
    assert child_committe(vote.id)
    # already supermajority

    if member_of_root():
        # just forward the vote to the leader
        # Q: But then childcommitte(vote.voter) would return false
        # in the leader, as it's a granchild, not a child
        send(vote, leader(vote.block.view + 1))
```

### Propose block
```python
def propose_block(view: View, quorum: Set[Vote] | Set[TimeoutMsg]):
    assert leader(view)
    assert leader_supermajority(quorum)

    qc = build_qc(votes)
    block = build_block(qc)
    broadcast(block)
```


### Timeout
```python
def local_timeout(new_overlay: Overlay):
    # make it so we don't vote or forward any more vote after this
    LAST_TIMEOUT_VIEW = CURRENT_VIEW
    # TODO: change overlay

    if member_of_leaf():
        timeout_msg = create_timeout(CURRENT_VIEW, LOCAL_HIGH_QC, LAST_TIMEOUT_VIEW_QC)
        send(timeout_msg, parent_committee())
```

### Receive
this is called *after* local_timeout
```python
def timeout(view: View, msgs: Set[TimeoutMsg]):
    assert supermajority(msgs)
    assert all(child_committee(msg.id) for msg in msgs)
    assert all(timeout.view == view for timeout in msgs)


    if CURRENT_VIEW > view:
        return
    if view <= LAST_VIEW_TIMEOUT_QC.view:
        return

    if view > LOCAL_HIGH_QC.view:
        LOCAL_HIGH_QC = timeout_Msg.high_qc

    timeout_qc = create_timeout_qc(msgs)
    increment_view_timeout_qc(timeout_qc.view)
    LAST_VIEW_TIMEOUT_QC = timeout_qc
    send(timeout_qc, own_committee()) ####helps nodes to sync quicker but not required
    if member_of_root():
        send(timeout_qc, leader(view+1))
    else:
        send(timeout_qc, parent_committee())
```


We need to make sure that qcs can't be removed from aggQc when going up the tree
