import random
from typing import List


class FisherYates:
    @staticmethod
    def shuffle(elements: List, entropy: bytes) -> List:
        """
        Fisher-Yates shuffling algorithm.
        In Python, random.shuffle implements the Fisher-Yates shuffling.
        https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
        https://softwareengineering.stackexchange.com/a/215780
        :param elements: elements to be shuffled
        :param entropy: a seed for deterministic sampling
        """
        out = elements.copy()
        random.seed(a=entropy, version=2)
        random.shuffle(out)
        # reset seed
        random.seed()
        return out
