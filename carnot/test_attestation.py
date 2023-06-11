import unittest

from PoS_attestation import *


class TestCountOnBitarrayFields(unittest.TestCase):
    def test_count_on_bitarray_fields(self):
        bitarrays = [[1, 0, 1], [0, 1, 1], [1, 1, 0]]
        majority_threshold = 2
        threshold2 = 1

        result = count_on_bitarray_fields(bitarrays, majority_threshold, threshold2)
        expected_result = [1, 1, 1]
        print("result is ", result)
        self.assertEqual(result, expected_result)



class TestCreateCommitteeBitArray(unittest.TestCase):
    class Vote:
        def __init__(self, voter):
            self.voter = voter

    def test_createCommitteeBitArray_with_smaller_committee_size(self):
        voters = [
            self.Vote("Alice"),
            self.Vote("Bob"),
            self.Vote("Charlie")
        ]
        committee_size = 2

        try:
            result = createCommitteeBitArray(voters, committee_size)
            self.fail("AssertionError should have been raised.")
        except AssertionError:
            pass


    def test_createCommitteeBitArray_with_larger_committee_size(self):
        voters = [
            self.Vote("Alice"),
            self.Vote("Bob"),
            self.Vote("Charlie"),
            self.Vote("Dave"),
            self.Vote("Eve")
        ]
        committee_size = 6

        result = createCommitteeBitArray(voters, committee_size)
        expected_result = [True, True, True, True, True, False]

        self.assertEqual(result, expected_result)
