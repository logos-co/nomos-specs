from numpy.random import Generator
from randomgen.chacha import ChaCha


class FisherYates:
    @staticmethod
    def shuffle(elements: list, entropy: bytes) -> list:
        out = elements.copy()
        rng = Generator(ChaCha(seed=list(entropy)))
        for i in reversed(range(1, len(out))):
            j = rng.integers(low=0, high=i, endpoint=True)  # [low,high]
            out[i], out[j] = out[j], out[i]
        return out
