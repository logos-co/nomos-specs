import unittest

import carnot
from carnot import merging_committees
from carnot.merging_committees import merge_committees
import itertools
import unittest
from carnot.carnot_vote_aggregation import Carnot2,StandardQc
class TestMergeCommittees(unittest.TestCase):

    def assertMergedSetsEqual(self, merged, original):
        merged_elements = set(itertools.chain.from_iterable(merged))
        self.assertEqual(merged_elements, original)

    def test_merge_committees_even(self):
        # Test merging when the number of committees is even
        original_sets = [set([1, 2, 3]), set([4, 5, 6]), set([7, 8, 9]), set([10, 11, 12])]
        merged = merge_committees(original_sets)
        self.assertMergedSetsEqual(merged, set.union(*original_sets))

    def test_merge_committees_odd(self):
        # Test merging when the number of committees is odd
        original_sets = [set([1, 2, 3]), set([4, 5, 6]), set([7, 8, 9])]
        merged = merge_committees(original_sets)
        self.assertMergedSetsEqual(merged, set.union(*original_sets))

    def test_merge_committees_empty(self):
        # Test merging when there are empty committees
        original_sets = [set([1, 2, 3]), set([]), set([4, 5, 6])]
        merged = merge_committees(original_sets)
        self.assertMergedSetsEqual(merged, set.union(*original_sets))



class TestConcatenateStandardQcs(unittest.TestCase):
    def test_concatenate_standard_qcs(self):
        # Create some StandardQc objects
        qc1 = StandardQc(block=1, view=1, voters={1, 2, 3})
        qc2 = StandardQc(block=1, view=1, voters={4, 5, 6})
        qc3 = StandardQc(block=1, view=1, voters={7, 8, 6})

        # Concatenate the StandardQc objects
        concatenated_qc = carnot.carnot_vote_aggregation.Carnot2.concatenate_standard_qcs({qc1, qc2, qc3})

        # Define the expected concatenated StandardQc
        expected_qc = StandardQc(block=1, view=1, voters={1, 2, 3, 4, 5, 6, 7, 8})

        # Assert that the concatenated StandardQc matches the expected one
        self.assertEqual(concatenated_qc, expected_qc)


if __name__ == '__main__':
    unittest.main()
