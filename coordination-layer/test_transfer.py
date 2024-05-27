from unittest import TestCase
from dataclasses import dataclass

from crypto import Field, prf
from note import InnerNote, PublicNote, SecretNote, nf_pk
from partial_transaction import PartialTransaction
from transaction_bundle import TransactionBundle

import constraints


class TestTransfer(TestCase):
    def test_1_to_1_transfer(self):
        # Alice wants to transfer ownership of a note to Bob.

        @dataclass
        class User:
            sk: Field

            @property
            def pk(self) -> Field:
                return nf_pk(self.sk)

        alice = User(sk=Field.random())
        bob = User(sk=Field.random())

        alices_note = SecretNote(
            note=InnerNote(
                value=100,
                unit="NMO",
                birth_constraint=constraints.Vacuous(),
                death_constraints=[constraints.Vacuous()],
                state=Field.zero(),
                nonce=Field.random(),
                rand=Field.random(),
            ),
            nf_sk=alice.sk,
        )

        bobs_note = PublicNote(
            note=InnerNote(
                value=100,
                unit="NMO",
                birth_constraint=constraints.Vacuous(),
                death_constraints=[constraints.Vacuous()],
                state=Field.zero(),
                nonce=Field.random(),
                rand=Field.random(),
            ),
            nf_pk=bob.pk,
        )

        ptx = PartialTransaction(
            inputs=[alices_note],
            outputs=[alices_note],
            rand=Field.random(),
        )

        bundle = TransactionBundle(bundle=[ptx])

        assert bundle.verify()
