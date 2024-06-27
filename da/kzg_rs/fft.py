from typing import Sequence, List

from eth2spec.deneb.mainnet import BLSFieldElement
from eth2spec.utils import bls

from da.kzg_rs.common import G1


def fft_g1(vals: Sequence[G1], roots_of_unity: Sequence[BLSFieldElement], modulus: int) -> List[G1]:
    if len(vals) == 1:
        return vals
    L = fft_g1(vals[::2], roots_of_unity[::2], modulus)
    R = fft_g1(vals[1::2], roots_of_unity[::2], modulus)
    o = [bls.Z1() for _ in vals]
    for i, (x, y) in enumerate(zip(L, R)):
        y_times_root = bls.multiply(y, roots_of_unity[i])
        o[i] = (x + y_times_root)
        o[i + len(L)] = x + -y_times_root
    return o


def ifft_g1(vals: Sequence[G1], roots_of_unity: Sequence[BLSFieldElement], modulus: int) -> List[G1]:
    assert len(vals) == len(roots_of_unity)
    # modular inverse
    invlen = pow(len(vals), modulus-2, modulus)
    return [
        bls.multiply(x, invlen)
        for x in fft_g1(
            vals, [roots_of_unity[0], *roots_of_unity[:0:-1]], modulus
        )
    ]


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
        y_times_root = BLSFieldElement((int(y) * int(roots_of_unity[i])) % modulus)
        o[i] = BLSFieldElement((int(x) + y_times_root) % modulus)
        o[i + len(L)] = BLSFieldElement((int(x) - int(y_times_root) + modulus) % modulus)
    return o


def fft(vals, root_of_unity, modulus):
    assert len(vals) == len(root_of_unity)
    return _fft(vals, root_of_unity, modulus)


def ifft(vals, roots_of_unity, modulus):
    assert len(vals) == len(roots_of_unity)
    # modular inverse
    invlen = pow(len(vals), modulus-2, modulus)
    return [
        BLSFieldElement((int(x) * invlen) % modulus)
        for x in _fft(
            vals, [roots_of_unity[0], *roots_of_unity[:0:-1]], modulus
        )
    ]
