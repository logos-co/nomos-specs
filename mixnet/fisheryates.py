import random
from typing import List


class FisherYates:
    @staticmethod
    def shuffle(elements: List, seed: bytes) -> List:
        """
        Fisher-Yates shuffling algorithm.
        In Python, random.shuffle implements the Fisher-Yates shuffling.
        https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
        https://softwareengineering.stackexchange.com/a/215780
        :param elements: elements to be shuffled
        :param entropy: a seed for deterministic sampling
        """
        random.seed(a=seed, version=2)
        out = elements.copy()
        random.shuffle(out)
        # reset seed
        random.seed()
        return out
