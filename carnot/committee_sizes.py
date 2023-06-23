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
    # N is the number of nodes, delta is the failure prob. which can be tolerated,
    # A is the fraction of a committee (typical value is  1/3) and P
    # is the fraction of adversarial nodes (typical value is 1/4).
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
        if 0 < remainder:
            committee_size_probability = binom.cdf(
                math.floor(adversaries_threshold_per_committee * committee_size),
                committee_size,
                network_adversary_threshold
            )
            committee_size_plus_one_probability = binom.cdf(
                math.floor(adversaries_threshold_per_committee * (committee_size + 1)),
                committee_size + 1,
                network_adversary_threshold
            )
            current_probability = 1 - committee_size_probability ** (number_of_committees - remainder) * committee_size_plus_one_probability ** remainder
        else:
            committee_size_probability = binom.cdf(
                math.floor(adversaries_threshold_per_committee * committee_size),
                committee_size,
                network_adversary_threshold
            )
            current_probability = 1 - committee_size_probability ** number_of_committees
    # return number of committees, K_1, committee size, n_1, number of committees
    # with size n_1+1, r_1 and prob. of failure, Prob_1.
    return previous_number_of_committees, previous_committee_size, previous_remainder, previous_probability
