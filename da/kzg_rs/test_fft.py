from unittest import TestCase

from da.kzg_rs.common import BLS_MODULUS
from fft import fft, ifft
from eth2spec.eip7594.mainnet import fft_field, BLSFieldElement


class TestFFT(TestCase):
    def test_fft_ifft(self):
        roots_of_unity = [pow(2, i, BLS_MODULUS) for i in range(8)]
        vals = list(BLSFieldElement(x) for x in range(8))
        vals_fft = fft_field(vals, roots_of_unity)
        self.assertEqual(vals, fft_field(vals_fft, roots_of_unity, inv=True))
