from dataclasses import dataclass


from constraints import Proof
from note import PublicNote, SecretNote
from crypto import Field, Point


@dataclass
class InputNote:
    note: SecretNote
    death_cm: Field  # commitment to the death constraint we are using
    death_proof: Proof

    def verify(self):
        # TODO: note.note is ugly
        return self.note.note.verify_death(self.death_cm, self.death_proof)


@dataclass
class OutputNote:
    note: PublicNote
    birth_proof: Proof

    def verify(self):
        # TODO: note.note is ugly
        return self.note.note.verify_birth(self.birth_proof)


@dataclass(unsafe_hash=True)
class PartialTransaction:
    inputs: list[InputNote]
    outputs: list[OutputNote]
    rand: Field

    def verify(self) -> bool:
        valid_inputs = all(i.verify() for i in self.inputs)
        valid_outputs = all(o.verify() for o in self.outputs)
        return valid_inputs and valid_outputs

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
