class Polynomial[T]:
    def __init__(self, coefficients, modulus):
        self.coefficients = coefficients
        self.modulus = modulus

    def __repr__(self):
        return "Polynomial({}, modulus={})".format(self.coefficients, self.modulus)

    def __add__(self, other):
        return Polynomial(
            [(a + b) % self.modulus for a, b in zip(self.coefficients, other.coefficients)],
            self.modulus
        )

    def __sub__(self, other):
        return Polynomial(
            [(a - b) % self.modulus for a, b in zip(self.coefficients, other.coefficients)],
            self.modulus
        )

    def __mul__(self, other):
        result = [0] * (len(self.coefficients) + len(other.coefficients) - 1)
        for i in range(len(self.coefficients)):
            for j in range(len(other.coefficients)):
                result[i + j] = (result[i + j] + self.coefficients[i] * other.coefficients[j]) % self.modulus
        return Polynomial(result, self.modulus)

    def div(self, divisor):
        """
        Fast polynomial division by using Extended Synthetic Division. Also works with non-monic polynomials.
        Taken from: https://rosettacode.org/wiki/Polynomial_synthetic_division#Python
        """
        # dividend and divisor are both polynomials, which are here simply lists of coefficients. Eg: x^2 + 3x + 5 will be represented as [1, 3, 5]
        out = list(reversed(self.coefficients))  # Copy the dividend
        normalizer = divisor[0]
        for i in range(len(self) - (len(divisor) - 1)):
            out[i] /= normalizer  # for general polynomial division (when polynomials are non-monic),
            # we need to normalize by dividing the coefficient with the divisor's first coefficient
            coef = out[i]
            if coef != 0:  # useless to multiply if coef is 0
                for j in range(1, len(divisor)):  # in synthetic division, we always skip the first coefficient of the divisor,
                    # because it's only used to normalize the dividend coefficients
                    out[i + j] += (-divisor[j] * coef) % self.modulus

        # The resulting out contains both the quotient and the remainder, the remainder being the size of the divisor (the remainder
        # has necessarily the same degree as the divisor since it's what we couldn't divide from the dividend), so we compute the index
        # where this separation is, and return the quotient and remainder.
        separator = -(len(divisor) - 1)
        return (
            Polynomial(list(reversed(out[:separator])), self.modulus),
            Polynomial(list(reversed(out[separator:])), self.modulus)
        )
        # return quotient, remainder.

    def __truediv__(self, other):
        return self.div(other)

    def __neg__(self):
        return Polynomial([-1 * c for c in self.coefficients], self.modulus)

    def __len__(self):
        return len(self.coefficients)

    def __iter__(self):
        return iter(self.coefficients)

    def __getitem__(self, item):
        return self.coefficients[item]

    def eval(self, element):
        return sum((pow(element, i)*x) % self.modulus for i, x in enumerate(self.coefficients))
