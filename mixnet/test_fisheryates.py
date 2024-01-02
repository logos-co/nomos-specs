from unittest import TestCase

from fisheryates import FisherYates


class TestFisherYates(TestCase):
    def test_shuffle(self):
        entropy = b"hello"
        elems = [1, 2, 3, 4, 5]

        shuffled1 = FisherYates.shuffle(elems, entropy)
        self.assertEqual(sorted(elems), sorted(shuffled1))

        # shuffle again with the same entropy
        shuffled2 = FisherYates.shuffle(elems, entropy)
        self.assertEqual(shuffled1, shuffled2)

        # shuffle with a different entropy
        shuffled3 = FisherYates.shuffle(elems, b"world")
        self.assertNotEqual(shuffled1, shuffled3)
        self.assertEqual(sorted(elems), sorted(shuffled3))
