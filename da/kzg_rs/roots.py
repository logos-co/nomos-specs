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
