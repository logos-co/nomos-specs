from typing import Sequence

from eth2spec.deneb.mainnet import BLSFieldElement


def _fft(
        vals: Sequence[BLSFieldElement],
        roots_of_unity: Sequence[BLSFieldElement],
        modulus: int,
) -> Sequence[BLSFieldElement]:
    if len(vals) == 1:
        return vals
    L = _fft(vals[::2], roots_of_unity[::2], modulus)
    R = _fft(vals[1::2], roots_of_unity[::2], modulus)
    o = [BLSFieldElement(0) for _ in vals]
    for i, (x, y) in enumerate(zip(L, R)):
        y_times_root = (int(y) * int(roots_of_unity[i])) % modulus
        o[i] = BLSFieldElement((int(x) + y_times_root) % modulus)
        o[i + len(L)] = BLSFieldElement((int(x) - y_times_root + modulus) % modulus)
    return o


def fft(vals, root_of_unity, modulus):
    assert len(vals) == len(root_of_unity)
    return _fft(vals, root_of_unity, modulus)


def ifft(vals, root_of_unity, modulus):
    assert len(vals) == len(root_of_unity)
    # modular inverse
    invlen = pow(len(vals), modulus-2, modulus)
    return [
        BLSFieldElement((int(x) * invlen) % modulus)
        for x in _fft(
            vals, [root_of_unity[0], *root_of_unity[:0:-1]], modulus
        )
    ]
