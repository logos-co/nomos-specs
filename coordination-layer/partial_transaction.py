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

    def verify(self) -> bool:
        raise NotImplementedError()

    def balance(self) -> Point:
        output_balance = sum((n.balance for n in self.outputs), start=Point.zero())
        # TODO: once again just mentioning this inefficiency. we are converting our private
        # inputs to public inputs to compute the balance, so we don't need an Output class,
        # we can directly compute the balance commitment from the public output notes.
        input_balance = sum(
            (n.to_public().balance(self.rand) for n in self.inputs), start=Point.zero()
        )
        return output_balance + input_balance.negate()

    # TODO: do we need this?
    def blinding(self) -> Field:
        return sum(outputs.blinding(self.rand)) - sum(outputs.blinding(self.rand))

    def zero(self) -> Field:
        output_zero = sum((n.zero for n in self.outputs), start=Point.zero())
        # TODO: once again just mentioning this inefficiency. we are converting our private
        # inputs to public inputs to compute the zero commitment, so we don't need an Output class,
        # we can directly compute the zero commitment from the public output notes.
        input_zero = sum(
            (n.to_public().zero(self.rand) for n in self.inputs), start=Point.zero()
        )

        return output_zero + input_zero.negate()
