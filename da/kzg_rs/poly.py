from itertools import zip_longest
from typing import List, Sequence, Self

from sympy import ntt, intt


class Polynomial[T]:
    def __init__(self, coefficients, modulus):
        self.coefficients = coefficients
        self.modulus = modulus

    @classmethod
    def from_evaluations(cls, evalutaions: Sequence[T], modulus) -> Self:
        coefficients = intt(evalutaions, prime=modulus)
        return cls(coefficients, modulus)

    def __repr__(self):
        return "Polynomial({}, modulus={})".format(self.coefficients, self.modulus)

    def __add__(self, other):
        return Polynomial(
            [(a + b) % self.modulus for a, b in zip_longest(self.coefficients, other.coefficients, fillvalue=0)],
            self.modulus
        )

    def __sub__(self, other):
        return Polynomial(
            [(a - b) % self.modulus for a, b in zip_longest(self.coefficients, other.coefficients, fillvalue=0)],
            self.modulus
        )

    def __mul__(self, other):
        result = [0] * (len(self.coefficients) + len(other.coefficients) - 1)
        for i in range(len(self.coefficients)):
            for j in range(len(other.coefficients)):
                result[i + j] = (result[i + j] + self.coefficients[i] * other.coefficients[j]) % self.modulus
        return Polynomial(result, self.modulus)

    def divide(self, other):
        if not isinstance(other, Polynomial):
            raise ValueError("Unsupported type for division.")

        dividend = list(self.coefficients)
        divisor = list(other.coefficients)

        quotient = []
        remainder = dividend

        while len(remainder) >= len(divisor):
            factor = remainder[-1] * pow(divisor[-1], -1, self.modulus) % self.modulus
            quotient.insert(0, factor)

            # Subtract divisor * factor from remainder
            for i in range(len(divisor)):
                remainder[len(remainder) - len(divisor) + i] -= divisor[i] * factor
                remainder[len(remainder) - len(divisor) + i] %= self.modulus

            # Remove leading zeros from remainder
            while remainder and remainder[-1] == 0:
                remainder.pop()

        return Polynomial(quotient, self.modulus), Polynomial(remainder, self.modulus)

    def __truediv__(self, other):
        return self.divide(other)

    def __neg__(self):
        return Polynomial([-1 * c for c in self.coefficients], self.modulus)

    def __len__(self):
        return len(self.coefficients)

    def __iter__(self):
        return iter(self.coefficients)

    def __getitem__(self, item):
        return self.coefficients[item]

    def __eq__(self, other):
        return self.coefficients == other.coefficients and self.modulus == other.modulus

    def eval(self, element):
        return sum(
            (pow(element, i)*x) % self.modulus for i, x in enumerate(self.coefficients)
        ) % self.modulus

    def evaluation_form(self) -> List[T]:
        return ntt(self.coefficients, prime=self.modulus)
