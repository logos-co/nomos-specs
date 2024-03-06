from itertools import zip_longest
from typing import List, Sequence, Self

from eth2spec.eip7594.mainnet import interpolate_polynomialcoeff

from da.kzg_rs.common import ROOTS_OF_UNITY


class Polynomial[T]:
    def __init__(self, coefficients, modulus):
        self.coefficients = coefficients
        self.modulus = modulus

    @staticmethod
    def interpolate(evaluations: List[int], roots_of_unity: List[int]) -> List[int]:
        """
        Lagrange interpolation

        Parameters:
            evaluations: List of evaluations
            roots_of_unity: Powers of 2 sequence

        Returns:
            list: Coefficients of the interpolated polynomial
        """
        return list(map(int, interpolate_polynomialcoeff(roots_of_unity[:len(evaluations)], evaluations)))

    @classmethod
    def from_evaluations(cls, evaluations: Sequence[T], modulus, roots_of_unity: Sequence[int]=ROOTS_OF_UNITY) -> Self:
        coefficients = [
            x % modulus
            for x in map(int, Polynomial.interpolate(evaluations, roots_of_unity))
        ]
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
        return (
            self.coefficients == other.coefficients and
            self.modulus == other.modulus
        )

    def eval(self, x):
        return (self.coefficients[0] + sum(
            (pow(x, i, mod=self.modulus)*coefficient)
            for i, coefficient in enumerate(self.coefficients[1:], start=1)
        )) % self.modulus

    def evaluation_form(self) -> List[T]:
        return [self.eval(ROOTS_OF_UNITY[i]) for i in range(len(self))]