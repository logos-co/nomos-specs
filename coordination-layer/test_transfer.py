from unittest import TestCase
from dataclasses import dataclass

from crypto import Field, prf
from note import InnerNote, PublicNote, SecretNote, nf_pk
from partial_transaction import PartialTransaction, Output
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

        tx_rand = Field.random()
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
        tx_output = Output(
            note=bobs_note,
            # TODO: why do we need an Output struct if we can
            # compute the balance and zero commitment form the
            # PublicNote itself?
            balance=bobs_note.balance(tx_rand),
            zero=bobs_note.zero(tx_rand),
        )

        ptx = PartialTransaction(
            inputs=[alices_note], outputs=[alices_note], rand=tx_rand
        )

        bundle = TransactionBundle(bundle=[ptx])

        assert bundle.verify()
