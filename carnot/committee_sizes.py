import math
from scipy.stats import binom


CARNOT_ADVERSARY_THRESHOLD_PER_COMMITTEE: float = 1/3
CARNOT_NETWORK_ADVERSARY_THRESHOLD: float = 1 / 4


def compute_optimal_number_of_committees_and_committee_size(
        number_of_nodes: int,
        failure_threshold: float,
        adversaries_threshold_per_committee: float,
        network_adversary_threshold: float
):
    assert failure_threshold > 0
    # number_of_nodes is the number of nodes in the network 
    # failure_threshold is the prob. of failure which can be tolerated
    # adversaries_threshold_per_committee is the fraction Byzantine modes in a committee
    # network_adversary_threshold is the fraction of Byzantine nodes in the network
    number_of_committees = 1
    committee_size = number_of_nodes
    remainder = 0
    current_probability = 0.0
    odd_committee = 0
    while current_probability < failure_threshold:
        previous_number_of_committees = number_of_committees
        previous_committee_size = committee_size
        previous_remainder = remainder
        previous_probability = current_probability
        odd_committee = odd_committee + 1
        number_of_committees = 2 * odd_committee + 1
        committee_size = number_of_nodes // number_of_committees
        remainder = number_of_nodes % number_of_committees

        committee_size_probability = binom.cdf(
            math.floor(adversaries_threshold_per_committee * committee_size),
            committee_size,
            network_adversary_threshold
        )
        if 0 < remainder:
            committee_size_plus_one_probability = binom.cdf(
                math.floor(adversaries_threshold_per_committee * (committee_size + 1)),
                committee_size + 1,
                network_adversary_threshold
            )
            current_probability = (
                    1 - committee_size_probability ** (number_of_committees - remainder)
                    * committee_size_plus_one_probability ** remainder
            )
        else:
            current_probability = 1 - committee_size_probability ** number_of_committees
    # return the number_of_committees, committee_size, remainder and current_probability
    # computed at the previous iteration. 
    return previous_number_of_committees, previous_committee_size, previous_remainder, previous_probability
