from dataclasses import dataclass

from note import PublicNote, SecretNote
from crypto import Field, Point


@dataclass
class Output:
    note: PublicNote

    # pre-computed balance and zero commitment "SecretNote" here.
    balance: Field
    zero: Field


@dataclass(unsafe_hash=True)
class PartialTransaction:
    inputs: list[SecretNote]
    outputs: list[Output]
    rand: Field

    def balance(self) -> Point:
        output_balance = sum(n.balance for n in self.outputs)
        input_balance = sum(n.note.balance() for n in self.inputs)
        return output_balance - input_balance

    def blinding(self) -> Field:
        return sum(outputs.blinding(self.rand)) - sum(outputs.blinding(self.rand))

    def zero(self) -> Field:
        return sum(outputs.note.zero(self.rand)) - sum(inputs.zero(self.rand))
