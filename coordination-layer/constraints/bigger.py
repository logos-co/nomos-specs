from dataclasses import dataclass

from .noir_constraint import NoirConstraint, NoirProof


@dataclass
class Bigger:
    """
    The statement "I know an `x` that is bigger than `y`".
    - `y` is a public parameter provided when the constraint is initialized
    - `x` is a secret parameter provided at proving time
    """

    y: int
    _noir = NoirConstraint("bigger")

    def prove(self, x: int) -> NoirProof:
        return self._noir.prove({"x": str(x), "y": str(self.y)})

    def verify(self, proof: NoirProof):
        return self._noir.verify({"y": str(self.y)}, proof)
