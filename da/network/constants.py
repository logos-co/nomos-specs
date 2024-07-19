from libp2p.typing import TProtocol

"""
    Some constants for use throught the poc 
"""

PROTOCOL_ID = TProtocol("/nomosda/1.0.0")
MAX_READ_LEN = 2**32 - 1
HASH_LENGTH = 256
NODE_PORT_BASE = 7560
EXECUTOR_PORT = 8766

# These can be overridden with cli params
DEFAULT_DATA_SIZE = 1024
DEFAULT_SUBNETS = 256
DEFAULT_NODES = 32
DEFAULT_SAMPLE_THRESHOLD = 12
# how many nodes per subnet minimum
DEFAULT_REPLICATION_FACTOR = 4

DEBUG = False
