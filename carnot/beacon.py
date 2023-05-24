# typing imports
from dataclasses import dataclass
from random import randint
from typing import TypeAlias

# carnot imports
# lib imports
from blspy import PrivateKey, Util, BasicSchemeMPL, G2Element, G1Element

# stdlib imports
from hashlib import sha256

View: TypeAlias = int
Sig: TypeAlias = bytes
Entropy: TypeAlias = bytes
PublicKey: TypeAlias = G1Element
VERSION = 0

def generate_random_sk() -> PrivateKey:
    seed = bytes([randint(0, 255) for _ in range(32)])
    return BasicSchemeMPL.key_gen(seed)


def view_to_bytes(view: View) -> bytes:
    return view.to_bytes((view.bit_length() + 7) // 8, byteorder='little', signed=True)

@dataclass
class RandomBeacon:
    version: int
    sig: Sig

    def entropy(self) -> Entropy:
        return self.sig


class NormalMode:

    @staticmethod
    def verify(beacon: RandomBeacon, pk: PublicKey, view: View) -> bool:
        """
        :param beacon: the provided beacon
        :param view: view to verify beacon upon
        :param pk: public key of the issuer of the beacon
        :return:
        """
        sig = G2Element.from_bytes(beacon.sig)
        return BasicSchemeMPL.verify(pk, view_to_bytes(view), sig)

    @staticmethod
    def generate_beacon(private_key: PrivateKey, view: View) -> RandomBeacon:
        return RandomBeacon(VERSION, bytes(BasicSchemeMPL.sign(private_key, view_to_bytes(view))))


class RecoveryMode:

    @staticmethod
    def verify(last_beacon: RandomBeacon, beacon: RandomBeacon, view: View) -> bool:
        """
        :param last_beacon: beacon for view - 1
        :param beacon: beacon for view
        :param view: the view to verify beacon upon
        :return:
        """
        b = sha256(last_beacon.entropy() + view_to_bytes(view)).digest()
        return b == beacon.entropy()

    @staticmethod
    def generate_beacon(last_beacon_entropy: Entropy, view: View) -> RandomBeacon:
        return RandomBeacon(VERSION, sha256(last_beacon_entropy + view_to_bytes(view)).digest())


class RandomBeaconHandler:
    def __init__(self, beacon: RandomBeacon):
        """
        :param beacon: Beacon should be initialized with either the last known working beacon from recovery.
        Or the hash of the genesis block in case of first consensus round.
        :return: Self
        """
        self.last_beacon: RandomBeacon = beacon

    def verify_happy(self, new_beacon: RandomBeacon, pk: PublicKey, view: View) -> bool:
        if NormalMode.verify(new_beacon, pk, view):
            self.last_beacon = new_beacon
            return True
        return False

    def verify_unhappy(self, new_beacon: RandomBeacon, view: View) -> bool:
        if RecoveryMode.verify(self.last_beacon, new_beacon, view):
            self.last_beacon = new_beacon
            return True
        return False
