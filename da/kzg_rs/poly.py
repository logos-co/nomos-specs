from typing import Self, List
from eth2spec.eip7594.mainnet import BLS_MODULUS
import numpy as np
from sympy import ntt, intt


class Polynomial[T](np.polynomial.Polynomial):
    def __init__(self, coef, domain=None, window=None, symbol="x"):
        self.coef = coef
        super().__init__(coef, domain, window, symbol)

    def eval(self, x: T) -> T:
        return np.polyval(self, x)

    def evaluation_form(self, modulus=BLS_MODULUS) -> Self:
        return Polynomial(intt(reversed(self), prime=modulus))

    # def __truediv__(self, other):
    #     return Polynomial(list(reversed(np.polydiv(list(reversed(self.coef)), list(reversed(other.coef))))))

    def __getitem__(self, item):
        return self.coef[item]
