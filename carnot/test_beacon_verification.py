from typing import Generator, Tuple
from unittest import TestCase

from blspy import AugSchemeMPL

from .beacon import *
from random import randint

class TestRandomBeaconVerification(TestCase):

    def happy_entropy_and_proof_generator(self) -> Generator[Tuple[Beacon, Proof], View, None]:
        while True:
            seed = bytes([randint(0, 255) for _ in range(32)])
            sk: PrivateKey = PopSchemeMPL.key_gen(seed)
            view = yield
            beacon = NormalMode.generate_beacon(sk, view)
            yield bytes(beacon), bytes(sk.get_g1())

    def unhappy_entropy_and_proof_generator(self) -> Generator[Tuple[Beacon, Proof], Tuple[Beacon, View], None]:
        while True:
            last_beacon, view = yield
            yield RecoveryMode.generate_beacon(last_beacon, view), b""

    def setUp(self):
        entropy_gen = self.happy_entropy_and_proof_generator()
        next(entropy_gen)
        entropy, proof = entropy_gen.send(0)
        self.beacon = BeaconHandler(
            beacon=RandomBeacon(
                version=0,
                context=0,
                entropy=entropy,
                proof=proof
            )
        )

    def test_happy(self):
        entropy_and_proof_gen = self.happy_entropy_and_proof_generator()
        for i in range(3):
            next(entropy_and_proof_gen)
            entropy, proof = entropy_and_proof_gen.send(i)
            new_beacon = RandomBeacon(
                    version=0,
                    context=i,
                    entropy=entropy,
                    proof=proof
                )
            self.beacon.verify_happy(new_beacon)
        assert self.beacon.last_beacon.context == 2

    def test_unhappy(self):
        entropy_and_proof_gen = self.unhappy_entropy_and_proof_generator()
        for i in range(1, 3):
            next(entropy_and_proof_gen)
            entropy, proof = entropy_and_proof_gen.send((self.beacon.last_beacon.entropy, i))
            new_beacon = RandomBeacon(
                version=0,
                context=i,
                entropy=entropy,
                proof=proof
            )
            self.beacon.verify_unhappy(new_beacon)
        assert self.beacon.last_beacon.context == 2
