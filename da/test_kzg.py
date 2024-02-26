from itertools import chain, batched
from random import randrange
from unittest import TestCase

from eth2spec.deneb.mainnet import BLS_MODULUS, bytes_to_bls_field

from da.kzg_rs import kzg
from da.kzg_rs.common import BYTES_PER_FIELD_ELEMENT, GLOBAL_PARAMETERS, ROOTS_OF_UNITY


class TestKZG(TestCase):

    @staticmethod
    def rand_bytes(size=1024):
        return bytearray(
            chain.from_iterable(
                int.to_bytes(randrange(BLS_MODULUS), length=BYTES_PER_FIELD_ELEMENT)
                for _ in range(size)
            )
        )

    def test_poly_forms(self):
        rand_bytes = self.rand_bytes(8)
        eval_form = [int(bytes_to_bls_field(b)) for b in batched(rand_bytes, int(BYTES_PER_FIELD_ELEMENT))]
        poly = kzg.bytes_to_polynomial(rand_bytes)
        self.assertEqual(poly.evaluation_form(), eval_form)
        self.assertEqual(poly.evaluation_form()[0], poly.eval(int(ROOTS_OF_UNITY[0])))

    def test_commitment(self):
        rand_bytes = self.rand_bytes(32)
        commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        self.assertEqual(len(commit), 48)

    def test_proof(self):
        rand_bytes = self.rand_bytes(2)
        poly = kzg.bytes_to_polynomial(rand_bytes)
        proof = kzg.generate_element_proof(0, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
        self.assertEqual(len(proof), 48)

    def test_verify(self):
        n_chunks = 32
        rand_bytes = self.rand_bytes(n_chunks)
        commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        poly = kzg.bytes_to_polynomial(rand_bytes)
        for n in range(n_chunks):
            proof = kzg.generate_element_proof(n, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
            self.assertEqual(len(proof), 48)
            self.assertTrue(kzg.verify_element_proof(
                poly, commit, proof, n, ROOTS_OF_UNITY
                )
            )
        proof = kzg.generate_element_proof(0, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
        for n in range(1, n_chunks):
            self.assertFalse(kzg.verify_element_proof(
                poly, commit, proof, n, ROOTS_OF_UNITY
                )
            )