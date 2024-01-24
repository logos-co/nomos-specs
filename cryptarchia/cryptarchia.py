

# Please note this is still a work in progress
from dataclasses import dataclass

Id: TypeAlias = bytes

@dataclass
class Epoch:
    # identifier of the epoch, counting incrementally from 0
    epoch: int

# An absolute unique indentifier of a slot, counting incrementally from 0
@dataclass
class Slot:
    absolute_slot: int

    def from_unix_timestamp_s(config: TimeConfig, timestamp_s: int) -> Date:
        absolute_slot = timestamp_s // config.slot_duration
        return Slot(absolute_slot)

    def epoch(self, config: TimeConfig) -> Epoch:
        return self.absolute_slot // config.slots_per_epoch


@dataclass
class TimeConfig:
    # How many slots in a epoch, all epochs will have the same number of slots
    slots_per_epoch: int
    # How long a slot lasts in seconds
    slot_duration: int
    # Start of the first epoch, in unix timestamp second precision
    chain_start_time: int


@dataclass 
class Config:
    k: int
    time: TimeConfig

@dataclass
class BlockHeader:
    slot: Slot
    parent: Id
    _id: Id  # this is an abstration over the block id

    def parent(self) -> Id:
        return self.parent

    def id(self) -> Id:
        return self._id


@dataclass 
class Chain:
    blocks: List[BlockHeader]

    def tip(self) -> BlockHeader:
        return self.blocks[-1]

    def length(self) -> int:
        return len(self.blocks)

    def contains_block(self, block: BlockHeader) -> bool:
        return block in self.blocks
    
    def block_position(self, block: BlockHeader) -> int:
        assert self.contains_block(block)
        for (i, b) in enumerate(self.blocks):
            if b == block:
                return i

class Follower:
    def __init__(self, genesis: BlockHeader, config: Config):
        self.config = config
        self.forks = []
        self.local_chain = Chain([genesis])

    # We don't do any validation in the current version
    def validate_header(block: BlockHeader) -> bool:
        True

    # Try appending this block to an existing chain and return whether
    # the operation was successful
    def try_extend_chains(self, block: BlockHeader) -> bool:
        if self.local_chain.tip().id() == block.parent():
            self.local_chain.blocks.append(block)
            return True
        
        for chain in self.forks:
            if chain.tip().id() == block.parent():
                chain.blocks.append(block)
                return True

        return False


    def try_create_fork(self, block: BlockHeader) -> Option[Chain]:
        chains = self.forks + [self.local_chain]
        for chain in chains:
            if self.chain.contains_block(block):
                block_position = chain.block_position(block)
                return Chain(blocks = chain.blocks[:block_position] + [block])
        
        return None

    def on_block(self, block: BlockHeader):
        if not self.validate_header(block):
            return

        # check if the new block extends an existing chain
        if self.try_extend_chains(block):
            return

        # if we get here, we might need to create a fork
        new_chain = self.try_create_fork(block)
        if new_chain is not None:
            self.forks.append(new_chain)
        # otherwise, we're missing the parent block
        # in that case, just ignore the block
        

    # Evaluate the fork choice rule and return the block header of the block that should be the head of the chain
    def fork_choice(local_chain: Chain, forks: List[Chain]) -> BlockHeader:
        pass
        

    def tip(self) -> BlockHeader:
        return self.fork_choice()


@dataclass
class Coin:
    value: int

class Leader:
    def init(self, genesis: BlockHeader, config: TimeConfig, coins: List[Coin]):
        self.config = config
        self.tip = genesis
        self.coins = coins

    def is_leader_at(self, slot: Slot) -> bool:
        for coin in self.coins:
            if lottery(slot, coin):
                return True
        return False
    
    def propose_block(self, slot: Slot, parent: BlockHeader) -> BlockHeader:
        assert self.is_leader_at(slot)
        return BlockHeader(parent=parent.id(), slot=slot, _id=Id(b"TODO"))


if __name__ == "__main__":
    pass