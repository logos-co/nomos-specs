from unittest import TestCase

from .roots import compute_roots_of_unity
from .common import BLS_MODULUS
from .fft import fft, ifft


class TestFFT(TestCase):
    def test_fft_ifft(self):
        for size in [16, 32, 64, 128, 256, 512, 1024, 2048, 4096]:
            roots_of_unity = compute_roots_of_unity(2, size, BLS_MODULUS)
            vals = list(x for x in range(size))
            vals_fft = fft(vals, roots_of_unity, BLS_MODULUS)
            self.assertEqual(vals, ifft(vals_fft, roots_of_unity, BLS_MODULUS))
