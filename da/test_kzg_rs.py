from itertools import chain
from random import randrange
from unittest import TestCase
from da.kzg_rs import Polynomial, bytes_to_polynomial, bytes_to_kzg_commitment, compute_kzg_proofs, setup_field_elements
from eth2spec.eip7594.mainnet import (
    Polynomial as EthPolynomial, blob_to_polynomial, BLS_MODULUS,
    BYTES_PER_FIELD_ELEMENT, FIELD_ELEMENTS_PER_BLOB, Blob, blob_to_kzg_commitment
)


class TestKzgRs(TestCase):

    @staticmethod
    def rand_bytes(size=FIELD_ELEMENTS_PER_BLOB):
        return bytearray(
            chain.from_iterable(
                int.to_bytes(randrange(BLS_MODULUS), length=BYTES_PER_FIELD_ELEMENT)
                for _ in range(size)
            )
        )

    def test_bytes_to_polynomial(self):
        rand_bytes = self.rand_bytes()
        eth_poly = blob_to_polynomial(Blob(rand_bytes))
        poly = bytes_to_polynomial(rand_bytes)
        self.assertEqual(eth_poly, poly)

    def test_bytes_to_kzg_commitment(self):
        rand_bytes = self.rand_bytes()
        eth_commitment = blob_to_kzg_commitment(Blob(rand_bytes))
        commitment = bytes_to_kzg_commitment(rand_bytes)
        self.assertEqual(eth_commitment, commitment)

    def test_small_bytes_kzg_commitment(self):
        rand_bytes = bytearray(int.to_bytes(randrange(BLS_MODULUS), length=BYTES_PER_FIELD_ELEMENT))
        commitment = bytes_to_kzg_commitment(rand_bytes)
        rand_bytes = self.rand_bytes()
        commitment2 = bytes_to_kzg_commitment(rand_bytes)
        self.assertEqual(len(commitment), len(commitment2))

    def test_compute_kzg_proofs(self):
        chunk_size = 32
        rand_bytes = self.rand_bytes(chunk_size)
        proofs = compute_kzg_proofs(rand_bytes)
        self.assertEqual(len(proofs), chunk_size)
