import unittest

import carnot
from carnot.carnot_vote_aggregation import  AggregateQc
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


class TestConcatenateAggregateQcs(unittest.TestCase):

    def test_concatenate_aggregate_qcs_single_qc(self):
        # Test concatenating a single AggregateQc
        qc1 = AggregateQc(
            sender_ids={1, 2, 3},
            qcs=[1, 2, 3],
            highest_qc=3,
            view=1
        )
        aggregate_qcs = {qc1}
        concatenated_qc = carnot.carnot_vote_aggregation.Carnot2.concatenate_aggregate_qcs(aggregate_qcs)
        self.assertEqual(concatenated_qc, qc1)

    def test_concatenate_aggregate_qcs_multiple_qcs(self):
        # Test concatenating multiple AggregateQcs
        qc1 = AggregateQc(
            sender_ids={1, 2, 3},
            qcs=[1, 2, 3],
            highest_qc=3,
            view=1
        )
        qc2 = AggregateQc(
            sender_ids={4, 5, 6},
            qcs=[4, 5, 6],
            highest_qc=6,
            view=2
        )
        qc3 = AggregateQc(
            sender_ids={7, 8, 9},
            qcs=[7, 8, 9],
            highest_qc=9,
            view=3
        )
        aggregate_qcs = {qc1, qc2, qc3}
        concatenated_qc = carnot.carnot_vote_aggregation.Carnot2.concatenate_aggregate_qcs(aggregate_qcs)

        # Assert that the concatenated AggregateQc has the correct attributes
        self.assertEqual(concatenated_qc.sender_ids, {1, 2, 3, 4, 5, 6, 7, 8, 9})
        self.assertEqual(concatenated_qc.qcs, [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(concatenated_qc.highest_qc, 9)
        self.assertEqual(concatenated_qc.view, 1)  # View should be from the first QC


if __name__ == '__main__':
    unittest.main()
