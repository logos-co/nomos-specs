from noir_constraint import NoirProof

from constraints import Constraint


class Vacuous(Constraint):
    """
    This is the empty constraint, it return true for any proof
    """

    def prove(self) -> NoirProof:
        return NoirProof("vacuous")

    def verify(self, _proof: NoirProof):
        return True
