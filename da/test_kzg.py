from itertools import chain
from random import randrange
from unittest import TestCase

from eth2spec.deneb.mainnet import BLS_MODULUS

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

    def test_commitment(self):
        rand_bytes = self.rand_bytes(32)
        commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        self.assertEqual(len(commit), 48)

    def test_proof(self):
        rand_bytes = self.rand_bytes(32)
        commit = kzg.bytes_to_commitment(rand_bytes, GLOBAL_PARAMETERS)
        poly = kzg.bytes_to_polynomial(rand_bytes)
        proof = kzg.generate_element_proof(poly[0], poly, GLOBAL_PARAMETERS)
        self.assertEqual(len(proof), 48)