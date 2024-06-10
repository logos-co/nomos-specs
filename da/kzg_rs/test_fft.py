from unittest import TestCase

from da.kzg_rs.common import BLS_MODULUS
from fft import fft, ifft


class TestFFT(TestCase):
    def test_fft_ifft(self):
        for size in [256, 512, 1024, 2048, 4096]:
            roots_of_unity = [pow(23674694431658770659612952115660802947967373701506253797663184111817857449850, i, BLS_MODULUS) for i in range(size)]
            vals = list(x for x in range(size))
            vals_fft = fft(vals, roots_of_unity, BLS_MODULUS)
            self.assertEqual(vals, ifft(vals_fft, roots_of_unity, BLS_MODULUS))

