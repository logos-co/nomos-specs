
def _simple_ft(vals, modulus, roots_of_unity):
    L = len(roots_of_unity)
    o = []
    for i in range(L):
        last = 0
        for j in range(L):
            last += vals[j] * roots_of_unity[(i*j)%L]
        o.append(last % modulus)
    return o


def _fft(vals, modulus, roots_of_unity):
    if len(vals) == 4:
        return _simple_ft(vals, modulus, roots_of_unity)
    if len(vals) == 1:
        return vals
    L = _fft(vals[::2], modulus, roots_of_unity[::2])
    R = _fft(vals[1::2], modulus, roots_of_unity[::2])
    o = [0 for _ in vals]
    for i, (x, y) in enumerate(zip(L, R)):
        y_times_root = (y*roots_of_unity[i]) % modulus
        o[i] = (x+y_times_root) % modulus
        o[i+len(L)] = (x-y_times_root+modulus) % modulus
    return o


def fft(vals, modulus, root_of_unity):
    assert len(vals) == len(root_of_unity)
    return _fft(vals, modulus, root_of_unity)


def ifft(vals, modulus, root_of_unity):
    assert len(vals) == len(root_of_unity)
    # modular inverse
    invlen = pow(len(vals), -1, modulus)
    return [(x * invlen) % modulus for x in _fft(vals, modulus, list(reversed(root_of_unity)))]
