from da.kzg_rs.common import BLS_MODULUS


def __fft(vals, modulus, roots_of_unity):
    if len(vals) == 1:
        return vals
    left = __fft(vals[::2], modulus, roots_of_unity[::2])
    right = __fft(vals[1::2], modulus, roots_of_unity[::2])
    o = [0 for _ in vals]
    for i, (x, y) in enumerate(zip(left, right)):
        y_times_root = y*int(roots_of_unity[i]) % modulus
        o[i] = (x+y_times_root) % modulus
        o[i+len(left)] = (x+modulus-y_times_root) % modulus
    return o


def fft(vals, modulus, roots_of_unity):
    return __fft(vals, modulus, roots_of_unity)


def ifft(vals, modulus, factor, roots_of_unity):
    # Inverse FFT
    invlen = pow(len(vals), modulus - factor, modulus)
    return [(x * invlen) % modulus for x in __fft(vals, modulus, roots_of_unity[:0:-1])]
