from typing import TypeAlias

import blspy

from mixnet.utils import random_bytes

BlsPrivateKey: TypeAlias = blspy.PrivateKey
BlsPublicKey: TypeAlias = blspy.G1Element


def generate_bls() -> BlsPrivateKey:
    seed = random_bytes(32)
    return blspy.BasicSchemeMPL.key_gen(seed)
