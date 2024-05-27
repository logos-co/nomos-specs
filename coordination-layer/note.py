from dataclasses import dataclass

from crypto import Field, Point, prf

from constraints import Constraint


@dataclass
class NoteCommitment:
    cm: Field
    blinding: Field
    zero: Field


@dataclass
class Nullifier:
    nf: bytes


def nf_pk(nf_sk) -> Field:
    return prf("CL_NOTE_NF", nf_sk)


@dataclass(unsafe_hash=True)
class InnerNote:
    value: Field
    unit: str
    birth_constraint: Constraint
    death_constraints: list[Constraint]
    state: Field
    nonce: Field
    rand: Field  # source of randomness for note commitment

    def r(self, index: int):
        prf("CL_NOTE_COMM_RAND", self.rand, index)

    def verify_value(self) -> bool:
        return 0 <= self.value and value <= 2**64

    @property
    def fungibility_domain(self) -> Field:
        """The fungibility domain of this note"""
        return crypto.prf(
            "CL_NOTE_NULL", self.birth_constraint.hash(), *crypto.str_to_vec(unit)
        )

    def death_constraints_root(self) -> Field:
        """
        Returns the merkle root over the set of death constraints
        """
        return crypto.merkle_root(self.death_constraints)


@dataclass(unsafe_hash=True)
class PublicNote:
    note: InnerNote
    nf_pk: Field

    def blinding(self, rand: Field) -> Field:
        """Blinding factor used in balance commitments"""
        return prf("CL_NOTE_BAL_BLIND", rand, self.nonce, self.nf_pk)

    def commit(self) -> Field:
        # blinding factors between data elems ensure no information is leaked in merkle paths
        return crypto.merkle_root(
            self.note.r(0),
            self.note.birth_constraint.hash(),
            self.note.r(1),
            self.note.death_constraints_root(),
            self.note.r(2),
            self.note.value,
            self.note.r(3),
            self.note.unit,
            self.note.r(4),
            self.note.state,
            self.note.r(5),
            self.note.nonce,
            self.note.r(6),
            self.nf_pk,
        )


@dataclass(unsafe_hash=True)
class SecretNote:
    note: InnerNote
    nf_sk: Field

    def to_public_note(self) -> PublicNote:
        return PublicNote(note=self.note, nf_pk=nf_pk(self.nf_sk))

    def nullifier(self):
        """
        The nullifier that must be provided when spending this note along
        with a proof that the nf_sk used to compute the nullifier corresponds
        to the nf_pk in the public note commitment.
        """
        return prf("NULLIFIER", self.nonce, self.nf_sk)

    def balance(self, rand):
        """
        Returns the pederson commitment to the notes value.
        """
        return crypto.pederson_commit(
            self.note.value, self.blinding(rand), self.note.fungibility_domain
        )

    def zero(self, rand):
        """
        Returns the pederson commitment to zero using the same blinding as the balance
        commitment.
        """
        return crypto.pederson_commit(
            0, self.blinding(rand), self.note.fungibility_domain
        )
