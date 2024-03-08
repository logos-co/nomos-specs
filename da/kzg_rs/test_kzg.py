from itertools import chain, batched
from random import randrange
from unittest import TestCase

from eth2spec.deneb.mainnet import BLS_MODULUS, bytes_to_bls_field, BLSFieldElement

from da.kzg_rs import kzg
from da.kzg_rs.common import BYTES_PER_FIELD_ELEMENT, GLOBAL_PARAMETERS, ROOTS_OF_UNITY, GLOBAL_PARAMETERS_G2
from da.kzg_rs.trusted_setup import verify_setup


class TestKZG(TestCase):

    @staticmethod
    def rand_bytes(n_chunks=1024):
        return bytes(
            chain.from_iterable(
                int.to_bytes(randrange(BLS_MODULUS), length=BYTES_PER_FIELD_ELEMENT)
                for _ in range(n_chunks)
            )
        )

    def test_kzg_setup(self):
        self.assertTrue(verify_setup((GLOBAL_PARAMETERS, GLOBAL_PARAMETERS_G2)))

    def test_poly_forms(self):
        n_chunks = 16
        rand_bytes = self.rand_bytes(n_chunks)
        eval_form = [int(bytes_to_bls_field(b)) for b in batched(rand_bytes, int(BYTES_PER_FIELD_ELEMENT))]
        poly = kzg.bytes_to_polynomial(rand_bytes)
        self.assertEqual(poly.evaluation_form(), eval_form)
        for i, chunk in enumerate(eval_form):
            self.assertEqual(poly.eval(ROOTS_OF_UNITY[i]), chunk)
        for i in range(n_chunks):
            self.assertEqual(poly.evaluation_form()[i], poly.eval(int(ROOTS_OF_UNITY[i])))

    def test_commitment(self):
        rand_bytes = self.rand_bytes(32)
        _, commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        self.assertEqual(len(commit), 48)

    def test_proof(self):
        rand_bytes = self.rand_bytes(2)
        poly = kzg.bytes_to_polynomial(rand_bytes)
        proof = kzg.generate_element_proof(0, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
        self.assertEqual(len(proof), 48)

    def test_verify(self):
        n_chunks = 32
        rand_bytes = self.rand_bytes(n_chunks)
        _, commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        poly = kzg.bytes_to_polynomial(rand_bytes)
        for i, chunk in enumerate(batched(rand_bytes, BYTES_PER_FIELD_ELEMENT)):
            chunk = bytes(chunk)
            proof = kzg.generate_element_proof(i, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
            self.assertEqual(len(proof), 48)
            self.assertEqual(poly.eval(int(ROOTS_OF_UNITY[i])), bytes_to_bls_field(chunk))
            self.assertTrue(kzg.verify_element_proof(
                bytes_to_bls_field(chunk), commit, proof, i, ROOTS_OF_UNITY
                )
            )
        proof = kzg.generate_element_proof(0, poly, GLOBAL_PARAMETERS, ROOTS_OF_UNITY)
        for n in range(1, n_chunks):
            self.assertFalse(kzg.verify_element_proof(
                BLSFieldElement(0), commit, proof, n, ROOTS_OF_UNITY
                )
            )