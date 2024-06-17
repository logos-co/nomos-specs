from typing import Tuple


def compute_root_of_unity(primitive_root: int, order: int, modulus: int) -> int:
    """
    Generate a w such that ``w**length = 1``.
    """
    assert (modulus - 1) % order == 0
    return pow(primitive_root, (modulus - 1) // order, modulus)


def compute_roots_of_unity(primitive_root: int, order: int, modulus: int) -> Tuple[int]:
    """
    Compute a list of roots of unity for a given order.
    The order must divide the BLS multiplicative group order, i.e. BLS_MODULUS - 1
    """
    assert (modulus - 1) % order == 0
    root_of_unity = compute_root_of_unity(primitive_root, order, modulus)

    roots = []
    current_root_of_unity = 1
    for _ in range(order):
        roots.append(current_root_of_unity)
        current_root_of_unity = current_root_of_unity * root_of_unity % modulus
    return tuple(roots)
