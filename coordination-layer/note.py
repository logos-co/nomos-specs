from dataclasses import dataclass

from crypto import Field, Point


@dataclass
class Commitment:
    cm: bytes


@dataclass
class Nullifier:
    nf: bytes


@dataclass
class SecretNote:
    note: InnerNote
    nf_sk: Field

    def to_public_note(self) -> PublicNote:
        return PublicNote(
            note=self.note,
            nf_pk=Point.generator().mul(self.nf_sk),
        )


@dataclass
class PublicNote:
    note: InnerNote
    nf_pk: Point

    def commit(self) -> Commitment:
        return crypto.COMM(
            self.note.birth_constraint.hash(),
            self.note.death_constraints_root(),
            self.note.value,
            self.note.unit,
            self.note.state,
            self.note.nonce,
            self.nf_pk,
        )


@dataclass
class InnerNote:
    value: Field
    unit: str
    birth_constraint: Constraint
    death_constraints: set[Constraint]
    state: Field
    nonce: Field
    rand: Field

    def death_constraints_root(self) -> Field:
        """
        Returns the merkle root over the set of death constraints
        """
        return crypto.merkle_root(self.death_constraints)
