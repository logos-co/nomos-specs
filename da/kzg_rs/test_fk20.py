from itertools import chain
from unittest import TestCase
import random
from .fk20 import fk20_generate_proofs
from .kzg import generate_element_proof, bytes_to_polynomial
from .common import BLS_MODULUS, BYTES_PER_FIELD_ELEMENT, GLOBAL_PARAMETERS, PRIMITIVE_ROOT
from .roots import compute_roots_of_unity


class TestFK20(TestCase):
    @staticmethod
    def rand_bytes(n_chunks=1024):
        return bytes(
            chain.from_iterable(
                int.to_bytes(random.randrange(BLS_MODULUS), length=BYTES_PER_FIELD_ELEMENT)
                for _ in range(n_chunks)
            )
        )

    def test_fk20(self):
        for size in [16, 32, 64, 128, 256]:
            roots_of_unity = compute_roots_of_unity(PRIMITIVE_ROOT, size, BLS_MODULUS)
            rand_bytes = self.rand_bytes(size)
            polynomial = bytes_to_polynomial(rand_bytes)
            proofs = [generate_element_proof(i, polynomial, GLOBAL_PARAMETERS, roots_of_unity) for i in range(size)]
            fk20_proofs = fk20_generate_proofs(polynomial, GLOBAL_PARAMETERS)
            self.assertEqual(len(proofs), len(fk20_proofs))
            self.assertEqual(proofs, fk20_proofs)
