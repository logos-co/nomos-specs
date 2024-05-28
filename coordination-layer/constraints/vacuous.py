from noir_constraint import NoirProof

from constraints import Constraint
from crypto import Field


class Vacuous(Constraint):
    """
    This is the empty constraint, it return true for any proof
    """

    def hash(self):
        # chosen by a fair 2**64 sided die.
        return Field(14500592324922987342)

    def prove(self) -> NoirProof:
        return NoirProof("vacuous")

    def verify(self, _proof: NoirProof):
        return True
