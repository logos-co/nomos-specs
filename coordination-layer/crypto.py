from keum import grumpkin
import poseidon


# !Important! The crypto primitives here must be in agreement with the proving system
# E.g. if you are using noir with the Barretenberg, we must use the Grumpkin curve.

Point = grumpkin.AffineWeierstrass
Field = grumpkin.Fq


def poseidon_grumpkin_field():
    # TODO: These parameters are made up.
    # return poseidon.Poseidon(
    #     p=Field.ORDER,
    #     security_level=128,
    #     alpha=5,
    #     input_rate=3,
    #     t=9,
    # )
    h, _ = poseidon.case_simple()

    # TODO: this is a hack to make poseidon take in arbitrary input length.
    # Fix is to implement a sponge as described in section 2.1 of
    # https://eprint.iacr.org/2019/458.pdf
    def inner(data):
        digest = 0
        for i in range(0, len(data), h.input_rate - 1):
            digest = h.run_hash([digest, *data[i : i + h.input_rate - 1]])
        return digest

    return inner


POSEIDON = poseidon_grumpkin_field()


def prf(domain, *elements):
    return POSEIDON(str_to_vec(domain) + elements)


def comm(*elements):
    """
    Returns a commitment to the sequence of elements.

    The commitmtent can be opened at index 0..len(elements)
    """
    raise NotImplementedError()


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
    return data + [0] * to_pad


def _str_to_vec(s):
    return list(map(ord, s))
