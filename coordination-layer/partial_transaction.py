from dataclasses import dataclass


from constraints import Proof
from note import PublicNote, SecretNote
from crypto import Field, Point


@dataclass
class InputNote:
    note: SecretNote
    death_proof: Proof

    def verify(self):
        return self.note.verify_death(self.death_proof)


@dataclass
class OutputNote:
    note: PublicNote
    birth_proof: Proof

    def verify(self):
        return self.note.verify_birth(self.birth_proof)


# TODO: is this used?
@dataclass
class Output:
    note: PublicNote

    # pre-computed balance and zero commitment "SecretNote" here.
    balance: Field
    zero: Field


@dataclass(unsafe_hash=True)
class PartialTransaction:
    inputs: list[InputNote]
    outputs: list[OutputNote]
    rand: Field

    def verify(self) -> bool:
        valid_inputs = all(i.verify() for i in self.inputs)
        valid_outputs = all(o.verify() for o in self.outputs)
        return valid_inputs and valid_output

    def balance(self) -> Point:
        output_balance = sum(
            (n.note.balance(self.rand) for n in self.outputs),
            start=Point.zero(),
        )
        input_balance = sum(
            (n.note.to_public().balance(self.rand) for n in self.inputs),
            start=Point.zero(),
        )
        return output_balance + input_balance.negate()

    # TODO: do we need this?
    def blinding(self) -> Field:
        return sum(outputs.blinding(self.rand)) - sum(outputs.blinding(self.rand))

    def zero(self) -> Field:
        output_zero = sum(
            (n.note.zero(self.rand) for n in self.outputs),
            start=Point.zero(),
        )
        input_zero = sum(
            (n.note.to_public().zero(self.rand) for n in self.inputs),
            start=Point.zero(),
        )

        return output_zero + input_zero.negate()
