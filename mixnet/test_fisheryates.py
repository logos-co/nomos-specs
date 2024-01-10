from unittest import TestCase

from mixnet.fisheryates import FisherYates


class TestFisherYates(TestCase):
    def test_shuffle(self):
        entropy = b"hello"
        elems = [1, 2, 3, 4, 5]

        sampled1 = FisherYates.sample(elems, 3, entropy)
        self.assertEqual(len(sampled1), 3)
        self.assertEqual(
            len(set(sampled1)), len(sampled1)
        )  # check if sampled elements are unique

        # sample again with the same entropy
        sampled2 = FisherYates.sample(elems, 3, entropy)
        self.assertEqual(sampled1, sampled2)

        # sample with a different entropy
        sampled3 = FisherYates.sample(elems, 3, b"world")
        self.assertNotEqual(sampled1, sampled3)
