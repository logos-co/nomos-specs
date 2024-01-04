def zero_bytes(size: int) -> bytes:
    assert size >= 0
    return bytes([0 for _ in range(size)])
