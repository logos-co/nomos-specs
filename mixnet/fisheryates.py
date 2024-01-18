import random
from typing import List


class FisherYates:
    @staticmethod
    def set_seed(seed: bytes) -> None:
        random.seed(a=seed, version=2)

    @staticmethod
    def shuffle(elements: List) -> List:
        """
        Fisher-Yates shuffling algorithm.
        In Python, random.shuffle implements the Fisher-Yates shuffling.
        https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
        https://softwareengineering.stackexchange.com/a/215780
        :param elements: elements to be shuffled
        :param entropy: a seed for deterministic sampling
        """
        out = elements.copy()
        random.shuffle(out)
        return out
