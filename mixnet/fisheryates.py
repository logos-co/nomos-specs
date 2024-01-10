import random
from typing import List


class FisherYates:
    @staticmethod
    def sample(elements: List, count: int, entropy: bytes) -> List:
        """
        A sampling algorithm using Fisher-Yates shuffling.
        In Python, random.sample uses Fisher-Yates shuffling internally by default.
        https://softwareengineering.stackexchange.com/a/215780
        https://docs.python.org/3/library/random.html#random.shuffle

        If FisherYates shuffling is not provided by a certain programming language by default,
        a developer has to implement FisherYates shuffling that can be used for sampling.
        https://en.wikipedia.org/wiki/Fisher%E2%80%93Yates_shuffle
        :param elements: elements that will be used for sampling
        :param count: the number of elements to be sampled
        :param entropy: a seed for deterministic sampling
        """
        random.seed(a=entropy, version=2)
        sampled = random.sample(elements, count)
        # reset seed
        random.seed()
        return sampled
