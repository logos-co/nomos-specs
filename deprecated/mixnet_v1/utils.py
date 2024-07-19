from random import randint


def random_bytes(size: int) -> bytes:
    assert size >= 0
    return bytes([randint(0, 255) for _ in range(size)])
