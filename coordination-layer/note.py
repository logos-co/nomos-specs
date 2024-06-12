from dataclasses import dataclass

from crypto import (
    Field,
    Point,
    prf,
    pederson_commit,
    _str_to_vec,
    merkle_root,
    hash_to_curve,
)

from constraints import Constraint, Proof


def nf_pk(nf_sk) -> Field:
    return prf("CL_NOTE_NF", nf_sk)


def balance_commitment(value: Field, tx_rand: Field, funge: Point):
    return pederson_commit(value, tx_rand, funge)


@dataclass(unsafe_hash=True)
class InnerNote:
    value: Field
    unit: str
    # TODO: inner notes should hold commitments to constraints.
    #       Constraints themselves will be stored in a key-value store
    birth_constraint: Constraint
    death_constraints: list[Constraint]
    state: Field
    nonce: Field
    rand: Field  # source of randomness for note commitment

    def __post_init__(self):
        if isinstance(self.value, int):
            self.value = Field(self.value)
        assert isinstance(self.value, Field), f"value is {type(self.value)}"
        assert isinstance(self.unit, str), f"unit is {type(self.unit)}"
        assert isinstance(
            self.birth_constraint, Constraint
        ), f"birth_constraint is {type(self.birth_constraint)}"
        assert isinstance(
            self.death_constraints, list
        ), f"death_constraints is {type(self.death_constraints)}"
        assert all(
            isinstance(d, Constraint) for d in self.death_constraints
        ), f"{[type(d) for d in self.death_constraints]}"
        assert isinstance(self.state, Field), f"state is {type(self.state)}"
        assert isinstance(self.nonce, Field), f"nonce is {type(self.nonce)}"
        assert isinstance(self.rand, Field), f"rand is {type(self.rand)}"

    def verify_death(self, death_cm: Field, death_proof: Proof) -> bool:
        constraint = [d for d in self.death_constraints if d.hash() == death_cm]
        if len(constraint) == 0:
            # given commitment was not one of the allowed death constraints
            return False

        constraint = constraint[0]

        # TODO: verifying the death constraint should include a commitment to the
        #       partial transaction so that the death constraint can make statements
        #       regarding the entire transaction.
        return constraint.verify(death_proof)

    def verify_birth(self, birth_proof: Proof) -> bool:
        # TODO: Should verifying the birth constraint include a commitment
        #       to the partial transaction?
        return self.birth_constraint.verify(birth_proof)

    def verify_value(self) -> bool:
        return 0 <= self.value and value <= 2**64

    def r(self, index: int):
        return prf("CL_NOTE_COMM_RAND", self.rand, index)

    @property
    def fungibility_domain(self) -> Point:
        """The fungibility domain of this note"""
        return hash_to_curve(
            "CL_NOTE_NULL", self.birth_constraint.hash(), *_str_to_vec(self.unit)
        )

    def death_constraints_root(self) -> Field:
        """
        Returns the merkle root over the set of death constraints
        """
        return merkle_root(self.death_constraints)


@dataclass(unsafe_hash=True)
class PublicNote:
    note: InnerNote
    nf_pk: Field

    def blinding(self, tx_rand: Field) -> Field:
        """Blinding factor used in balance commitments"""
        return prf("CL_NOTE_BAL_BLIND", tx_rand, self.note.nonce, self.nf_pk)

    def balance(self, tx_rand):
        """
        Returns the pederson commitment to the notes value.
        """
        return balance_commitment(
            self.note.value, self.blinding(tx_rand), self.note.fungibility_domain
        )

    def zero(self, tx_rand):
        """
        Returns the pederson commitment to the notes value.
        """
        return balance_commitment(
            Field.zero(), self.blinding(tx_rand), self.note.fungibility_domain
        )

    def commit(self) -> Field:
        # blinding factors between data elems ensure no information is leaked in merkle paths
        return merkle_root(
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

    def to_public(self) -> PublicNote:
        return PublicNote(note=self.note, nf_pk=nf_pk(self.nf_sk))

    def nullifier(self):
        """
        The nullifier that must be provided when spending this note along
        with a proof that the nf_sk used to compute the nullifier corresponds
        to the nf_pk in the public note commitment.
        """
        return prf("NULLIFIER", self.nonce, self.nf_sk)