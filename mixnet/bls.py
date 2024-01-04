from random import randint
from typing import TypeAlias

import blspy

BlsPrivateKey: TypeAlias = blspy.PrivateKey
BlsPublicKey: TypeAlias = blspy.G1Element


def generate_bls() -> BlsPrivateKey:
    seed = bytes([randint(0, 255) for _ in range(32)])
    return blspy.BasicSchemeMPL.key_gen(seed)
