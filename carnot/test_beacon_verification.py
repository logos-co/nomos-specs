from typing import Generator, Tuple
from unittest import TestCase

from blspy import AugSchemeMPL

from .beacon import *
from random import randint


class TestRandomBeaconVerification(TestCase):

    @staticmethod
    def happy_entropy_and_proof(view: View) -> Tuple[Beacon, Proof]:
        seed = bytes([randint(0, 255) for _ in range(32)])
        sk: PrivateKey = PopSchemeMPL.key_gen(seed)
        beacon = NormalMode.generate_beacon(sk, view)
        return bytes(beacon), bytes(sk.get_g1())

    @staticmethod
    def unhappy_entropy(last_beacon: Beacon, view: View) -> Beacon:
        return RecoveryMode.generate_beacon(last_beacon, view)

    def setUp(self):
        entropy, proof = self.happy_entropy_and_proof(0)
        self.beacon = BeaconHandler(
            beacon=RandomBeacon(
                version=0,
                context=0,
                entropy=entropy,
                proof=proof
            )
        )

    def test_happy(self):
        for i in range(3):
            entropy, proof = self.happy_entropy_and_proof(i)
            new_beacon = RandomBeacon(
                    version=0,
                    context=i,
                    entropy=entropy,
                    proof=proof
                )
            self.beacon.verify_happy(new_beacon)
        self.assertEqual(self.beacon.last_beacon.context, 2)

    def test_unhappy(self):
        for i in range(1, 3):
            entropy = self.unhappy_entropy(self.beacon.last_beacon.entropy, i)
            new_beacon = RandomBeacon(
                version=0,
                context=i,
                entropy=entropy,
                proof=b""
            )
            self.beacon.verify_unhappy(new_beacon)
        self.assertEqual(self.beacon.last_beacon.context, 2)

    def test_mixed(self):
        for i in range(1, 6, 2):
            entropy, proof = self.happy_entropy_and_proof(i)
            new_beacon = RandomBeacon(
                version=0,
                context=i,
                entropy=entropy,
                proof=proof
            )
            self.beacon.verify_happy(new_beacon)
            entropy = self.unhappy_entropy(self.beacon.last_beacon.entropy, i+1)
            new_beacon = RandomBeacon(
                version=0,
                context=i+1,
                entropy=entropy,
                proof=b""
            )
            self.beacon.verify_unhappy(new_beacon)
        self.assertEqual(self.beacon.last_beacon.context, 6)
