# def __fft(vals, modulus, roots_of_unity):
#     if len(vals) == 1:
#         return vals
#     left = __fft(vals[::2], modulus, roots_of_unity[::2])
#     right = __fft(vals[1::2], modulus, roots_of_unity[::2])
#     o = [0 for _ in vals]
#     for i, (x, y) in enumerate(zip(left, right)):
#         y_times_root = y*int(roots_of_unity[i]) % modulus
#         o[i] = (x+y_times_root) % modulus
#         o[i+len(left)] = (x+modulus-y_times_root) % modulus
#     return o
#
#
# def fft(vals, modulus, roots_of_unity):
#     return __fft(vals, modulus, roots_of_unity)
#
#
# def ifft(vals, modulus, factor, roots_of_unity):
#     # Inverse FFT
#     invlen = pow(len(vals), modulus - factor, modulus)
#     return [(x * invlen) % modulus for x in __fft(vals, modulus, roots_of_unity[:0:-1])]

import math


def fft(x, p, roots_of_unity):
    """
    Compute the FFT of a sequence x modulo p using precomputed roots of unity.

    Parameters:
        x (list): Sequence of integers.
        p (int): Modulus.
        roots_of_unity (list): List of precomputed roots of unity modulo p.

    Returns:
        list: FFT of the sequence x.
    """
    N = len(x)
    if N == 1:
        return x
    even = fft(x[0::2], p, roots_of_unity)
    odd = fft(x[1::2], p, roots_of_unity)
    factor = 1
    result = [0] * N
    for i in range(N // 2):
        result[i] = (even[i] + factor * odd[i]) % p
        result[i + N // 2] = (even[i] - factor * odd[i]) % p
        factor = (factor * roots_of_unity[i]) % p
    return result


def ifft(y, p, inverse_roots_of_unity):
    """
    Compute the inverse FFT of a sequence y modulo p using precomputed inverse roots of unity.

    Parameters:
        y (list): Sequence of integers.
        p (int): Modulus.
        inverse_roots_of_unity (list): List of precomputed inverse roots of unity modulo p.

    Returns:
        list: Inverse FFT of the sequence y.
    """
    N = len(y)
    if N == 1:
        return y
    even = ifft(y[0::2], p, inverse_roots_of_unity)
    odd = ifft(y[1::2], p, inverse_roots_of_unity)
    factor = 1
    result = [0] * N
    for i in range(N // 2):
        result[i] = (even[i] + factor * odd[i]) % p
        result[i + N // 2] = (even[i] - factor * odd[i]) % p
        factor = (factor * inverse_roots_of_unity[i]) % p
    return result


def find_inverse_primitive_root(primitive_root, p):
    """
    Find the inverse primitive root modulo p.

    Parameters:
        primitive_root (int): Primitive root modulo p.
        p (int): Modulus.

    Returns:
        int: Inverse primitive root modulo p.
    """
    return pow(primitive_root, p - 2, p)


def compute_roots_of_unity(primitive_root, p, n):
    """
    Compute the roots of unity modulo p.

    Parameters:
        primitive_root (int): Primitive root modulo p.
        p (int): Modulus.
        n (int): Number of roots of unity to compute.

    Returns:
        list: List of roots of unity modulo p.
    """
    roots_of_unity = [pow(primitive_root, i, p) for i in range(n)]
    return roots_of_unity


def compute_inverse_roots_of_unity(primitive_root, p, n):
    """
    Compute the inverse roots of unity modulo p.

    Parameters:
        primitive_root (int): Primitive root modulo p.
        p (int): Modulus.
        n (int): Number of roots of unity to compute.

    Returns:
        list: List of inverse roots of unity modulo p.
    """
    inverse_primitive_root = find_inverse_primitive_root(primitive_root, p)
    inverse_roots_of_unity = [pow(inverse_primitive_root, i, p) for i in range(n)]
    return inverse_roots_of_unity
