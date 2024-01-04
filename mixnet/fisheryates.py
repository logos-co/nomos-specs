from typing import List

from numpy.random import Generator
from randomgen.chacha import ChaCha


class FisherYates:
    @staticmethod
    def shuffle(elements: List, entropy: bytes) -> List:
        out = elements.copy()
        rng = Generator(ChaCha(seed=list(entropy)))
        for i in reversed(range(1, len(out))):
            j = rng.integers(low=0, high=i, endpoint=True)  # [low,high]
            out[i], out[j] = out[j], out[i]
        return out
