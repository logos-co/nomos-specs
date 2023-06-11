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


