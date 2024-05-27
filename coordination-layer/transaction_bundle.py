from dataclasses import dataclass

from partial_transaction import PartialTransaction
from crypto import Field


@dataclass
class TransactionBundle:
    bundle: list[PartialTransaction]

    def is_balanced(self) -> bool:
        # TODO: move this to a NOIR constraint
        return Field.zero() == sum(ptx.balance() - ptx.zero() for ptx in self.bundle)

    def verify(self) -> bool:
        return self.is_balanced() and all(ptx.verify() for ptx in self.bundle)
