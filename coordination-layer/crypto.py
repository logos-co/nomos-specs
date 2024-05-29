from keum import grumpkin
import poseidon


# !Important! The crypto primitives here must be in agreement with the proving system
# E.g. if you are using noir with the Barretenberg, we must use the Grumpkin curve.

Point = grumpkin.AffineWeierstrass
Field = grumpkin.Fq


def fake_algebraic_hash(data) -> Field:
    """
    HACK: we'll fake the algebraic hash using sha256(data) % Field.ORDER
    """
    assert all(isinstance(d, Field) for d in data), f"{data}\n{[type(d) for d in data]}"
    data = b"".join(d.v.to_bytes(256 // 8) for d in data)

    from hashlib import sha256

    return Field(int(sha256(data).hexdigest(), 16))


def build_poseidon():
    h = poseidon.Poseidon(
        p=Field.ORDER,
        security_level=128,
        alpha=5,
        input_rate=3,
        t=9,
    )

    # TODO: this is hacks on hacks to make poseidon take in arbitrary input length.
    # Fix is to implement a sponge as described in section 2.1 of
    # https://eprint.iacr.org/2019/458.pdf
    def inner(data):

        digest = 0
        for i in range(0, len(data), h.input_rate - 1):
            digest = h.run_hash([digest, *data[i : i + h.input_rate - 1]])
        return Field(int(digest))

    return inner


# HASH = build_poseidon()
HASH = fake_algebraic_hash


def prf(domain, *elements) -> Field:
    return HASH([*_str_to_vec(domain), *elements])


def hash_to_curve(domain, *elements) -> Point:
    # HACK: we don't currently have a proper hash_to_curve implementation
    # so we hack the Point.random() function.
    #
    # Point.random() calls into the global `random` module to generate a
    # point. We will seed the random module with the result of hashing the
    # elements and then call Point.random() to retreive the point
    # corresponding to the mentioned elements.

    r = prf(f"HASH_TO_CURVE_{domain}", *elements)

    import random

    random.seed(r.v)
    return Point.random()


def comm(*elements):
    """
    Returns a commitment to the sequence of elements.

    The commitmtent can be opened at index 0..len(elements)
    """
    raise NotImplementedError()


def pederson_commit(value: Field, blinding: Field, domain: Point) -> Point:
    return Point.generator().mul(value) + domain.mul(blinding)


def merkle_root(data) -> Field:
    data = _pad_to_power_of_2(data)
    nodes = [CRH(d) for d in data]
    while len(nodes) > 1:
        nodes = [CRH(nodes[i], nodes[i + 1]) for i in range(0, len(nodes), 2)]

    return nodes[0]


def _pad_to_power_of_2(data):
    import math

    max_lower_bound = int(math.log2(len(data)))
    if 2**max_lower_bound == len(data):
        return data
    to_pad = 2 ** (max_lower_bound + 1) - len(data)
    return data + [Field.zero()] * to_pad


def _str_to_vec(s):
    return [Field(ord(c)) for c in s]
