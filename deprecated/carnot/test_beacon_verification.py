from typing import Tuple
from unittest import TestCase

from carnot.beacon import *
from random import randint


class TestRandomBeaconVerification(TestCase):

    @staticmethod
    def happy_beacon_and_pk(view: View) -> Tuple[RandomBeacon, PublicKey]:
        sk = generate_random_sk()
        beacon = NormalMode.generate_beacon(sk, view)
        return beacon, sk.get_g1()

    @staticmethod
    def unhappy_beacon(last_beacon: Entropy, view: View) -> RandomBeacon:
        return RecoveryMode.generate_beacon(last_beacon, view)

    def setUp(self):
        beacon, pk = self.happy_beacon_and_pk(0)
        self.beacon = RandomBeaconHandler(beacon)

    def test_happy(self):
        for i in range(3):
            new_beacon, pk = self.happy_beacon_and_pk(i)
            self.beacon.verify_happy(new_beacon, pk, i)

    def test_unhappy(self):
        for i in range(1, 3):
            new_beacon = self.unhappy_beacon(self.beacon.last_beacon.entropy(), i)
            self.beacon.verify_unhappy(new_beacon, i)

    def test_mixed(self):
        for i in range(1, 6, 2):
            new_beacon, pk = self.happy_beacon_and_pk(i)
            self.beacon.verify_happy(new_beacon, pk, i)
            new_beacon = self.unhappy_beacon(self.beacon.last_beacon.entropy(), i+1)
            self.beacon.verify_unhappy(new_beacon, i+1)
