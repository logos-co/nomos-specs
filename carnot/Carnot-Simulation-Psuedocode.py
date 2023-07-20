import time


class Committee:
    def __init__(self, committee_id, processing_time=0, parent_committee=None):
        self.committee_id = committee_id
        self.child_committee = None
        self.parent_committee = parent_committee
       # self.processing_time = processing_time

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

    processing_time = 1  # Set the processing time for each committee (you can adjust this as needed)
    committee = Committee(committee_id, processing_time, parent_committee)
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

