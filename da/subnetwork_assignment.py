from itertools import chain
from math import ceil
from typing import Generator, Set, TypeAlias
from hashlib import blake2b
import random
from scipy.stats.qmc import Halton
Id: TypeAlias = bytes


def _lazy_recursive_hash(_id: Id, hasher=lambda x: blake2b(x).digest()) -> Generator[Id, None, None]:
    while True:
        _id = hasher(_id)
        yield _id


def generate_distribution_set(_id: Id, set_size: int, modulus=4096, hasher=lambda x: blake2b(x).digest()) -> Set[int]:
    result_set = set()
    ids = _lazy_recursive_hash(_id)
    while len(result_set) < set_size:
        result_set.add(int.from_bytes(next(ids)) % modulus)
    return result_set


def generate_distribution_set_v3(_id: Id, set_size: int, replication_factor: int, modulus=4096) -> Set[int]:
    halton = Halton(set_size*replication_factor, seed=int.from_bytes(_id))
    return set(chain.from_iterable(halton.integers(l_bounds=0, u_bounds=modulus, n=set_size*replication_factor)))


def calculate_minimum_membership(network_size: int, number_of_nodes: int, replication_factor: int) -> int:
    return ceil(network_size / number_of_nodes) * replication_factor

