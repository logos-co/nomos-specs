from dataclasses import dataclass

from partial_transaction import PartialTransaction
from crypto import Field, Point


@dataclass
class TransactionBundle:
    bundle: list[PartialTransaction]

    def is_balanced(self) -> bool:
        # TODO: move this to a NOIR constraint
        balance_commitment = sum(
            (ptx.balance() + ptx.zero().negate() for ptx in self.bundle),
            start=Point.zero(),
        )
        return Point.zero() == balance_commitment

    def verify(self) -> bool:
        return self.is_balanced() and all(ptx.verify() for ptx in self.bundle)
