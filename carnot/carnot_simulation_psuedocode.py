import time


class Committee:
    def __init__(self, committee_id, parent_committee=None):
        self.committee_id = committee_id
        self.child_committee = None
        self.parent_committee = parent_committee

def create_binary_tree_committees(num_levels, committee_id=0, parent_committee=None):
    """
    Creates a binary tree of committees given the number of levels.

    Parameters:
        num_levels (int): The number of levels in the binary tree.
        committee_id (int): The ID of the committee (represents the level in the binary tree).
        parent_committee (Committee): The parent committee.

    Returns:
        Committee: The root committee representing the entire binary tree.
    """
    if num_levels == 0:
        return None

    committee = Committee(committee_id,  parent_committee)
    committee.child_committee = create_binary_tree_committees(num_levels - 1, committee_id + 1, committee)
    return committee


def find_leaf_committee(committee):
    """
    Find the leaf committee at the lowest level.

    Parameters:
        committee (Committee): The committee representing a level in the binary tree.

    Returns:
        Committee: The leaf committee at the lowest level.
    """
    if committee.child_committee is None:
        return committee
    return find_leaf_committee(committee.child_committee)

def simulate_message_passing(committee, latency):
    """
    Simulates the message passing from a committee to its parent committee.

    Parameters:
        committee (Committee): The committee representing a level in the binary tree.

    Returns:
        int: The number of levels the message passed through.
    """
    # Base case: if the committee is the root (no parent), return 0 (the message reached the root)
    time.sleep(latency)
    print(committee.committee_id)
    if committee.parent_committee is None:
        return 0
    # Simulate the message passing to the parent committee and get its result
    parent_result = simulate_message_passing(committee.parent_committee,latency)

    # Increment the parent result by 1 (to count the current level) and return it
    return parent_result + 1

