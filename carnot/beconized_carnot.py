from carnot import Carnot, Block, TimeoutQc
from beacon import *


class BeaconizedBlock(Block):
    beacon: RandomBeacon

class BeaconizedCarnot(Carnot):
    def __int__(self):
        self.sk = generate_random_sk()
        self.pk = bytes(self.sk.get_gq())
        self.random_beacon = RandomBeaconHandler(
            RandomBeacon(
                version=0,
                context=-1,
                entropy=NormalMode.generate_beacon(self.sk, -1),
                proof=self.pk
            )
        )
        super(Carnot, self).__init__(self.pk)

    def receive_block(self, block: BeaconizedBlock):
        super(Carnot, self).receive_block(block)
        if self.block_is_safe(block):
            self.random_beacon.verify_happy(block.beacon)

    def receive_timeout_qc(self, timeout_qc: TimeoutQc):
        super(Carnot, self).receive_timeout_qc(timeout_qc)
        if timeout_qc.view < self.current_view:
            return
        entropy = RecoveryMode.generate_beacon(self.random_beacon.last_beacon.entropy, self.current_view)
        new_beacon = RandomBeacon(
            version=0,
            context=self.current_view,
            entropy=entropy,
            proof=b""
        )
        self.random_beacon.verify_unhappy(new_beacon)