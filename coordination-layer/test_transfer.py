from unittest import TestCase
from dataclasses import dataclass

from crypto import Field, prf
from note import InnerNote, PublicNote, SecretNote, nf_pk
from partial_transaction import PartialTransaction, InputNote, OutputNote
from transaction_bundle import TransactionBundle

from constraints import Vacuous


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
                birth_constraint=Vacuous(),
                death_constraints=[Vacuous()],
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
                birth_constraint=Vacuous(),
                death_constraints=[Vacuous()],
                state=Field.zero(),
                nonce=Field.random(),
                rand=Field.random(),
            ),
            nf_pk=bob.pk,
        )

        ptx = PartialTransaction(
            inputs=[
                InputNote(
                    note=alices_note,
                    death_cm=Vacuous().hash(),
                    death_proof=Vacuous().prove(),
                )
            ],
            outputs=[
                OutputNote(
                    note=bobs_note,
                    birth_proof=Vacuous().prove(),
                )
            ],
            rand=tx_rand,
        )

        bundle = TransactionBundle(bundle=[ptx])

        assert bundle.verify()
