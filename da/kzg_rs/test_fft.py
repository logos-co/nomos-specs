from unittest import TestCase

from da.kzg_rs.common import BLS_MODULUS, ROOTS_OF_UNITY, INVERSE_ROOTS_OF_UNITY
from da.kzg_rs.fft import fft, ifft
from da.kzg_rs.poly import Polynomial
from da.kzg_rs.rs import encode, decode


class TestFFT(TestCase):

    def test_encode_decode(self):
        poly = Polynomial(list(range(10)), modulus=BLS_MODULUS)
        encoded = encode(poly, 2, ROOTS_OF_UNITY)
        decoded = decode(encoded, ROOTS_OF_UNITY, len(poly))
        self.assertEqual(poly, decoded)
        for i in range(len(poly)):
            self.assertEqual(poly.eval(ROOTS_OF_UNITY[i]), decoded.eval(ROOTS_OF_UNITY[i]))
