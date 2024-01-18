from unittest import TestCase

from mixnet.fisheryates import FisherYates


class TestFisherYates(TestCase):
    def test_shuffle(self):
        elems = [1, 2, 3, 4, 5]

        FisherYates.set_seed(b"seed1")
        shuffled1 = FisherYates.shuffle(elems)
        self.assertEqual(sorted(elems), sorted(shuffled1))
        shuffled1_1 = FisherYates.shuffle(elems)
        self.assertNotEqual(shuffled1_1, shuffled1)

        # shuffle again with the same seed
        FisherYates.set_seed(b"seed1")
        shuffled2 = FisherYates.shuffle(elems)
        self.assertEqual(shuffled1, shuffled2)

        # shuffle with a different seed
        FisherYates.set_seed(b"seed2")
        shuffled3 = FisherYates.shuffle(elems)
        self.assertNotEqual(shuffled1, shuffled3)
        self.assertEqual(sorted(elems), sorted(shuffled3))
