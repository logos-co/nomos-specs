import unittest

import carnot
from carnot import merging_committees
from carnot.merging_committees import merge_committees
import itertools
import unittest

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

if __name__ == '__main__':
    unittest.main()
