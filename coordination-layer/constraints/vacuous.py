from constraints import Constraint, Proof
from crypto import Field


class Vacuous(Constraint):
    """
    This is the empty constraint, it return true for any proof
    """

    def hash(self):
        # chosen by a fair 2**64 sided die.
        return Field(14500592324922987342)

    def prove(self) -> Proof:
        return Proof()

    def verify(self, _proof: Proof):
        return True
