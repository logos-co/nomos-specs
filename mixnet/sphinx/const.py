# k in the Sphinx paper
SECURITY_PARAMETER = 16
# r in the Sphinx paper
# In this specification, the max number of mix nodes in a route is limited to this value.
MAX_PATH_LENGTH = 5
# The length of node address which contains an IP address and a port.
NODE_ADDRESS_LENGTH = 2 * SECURITY_PARAMETER
# The length of flag that represents the type of routing information (forward-hop or final-hop)
FLAG_LENGTH = 1

VERSION_LENGTH = 3
VERSION = b"\x00\x00\x00"

# In our architecture, SURB is not used.
# But, for the consistency with Nym's Sphinx implementation, keep this field in the Sphinx header.
SURB_IDENTIFIER_LENGTH = SECURITY_PARAMETER
SURB_IDENTIFIER = b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"

# In our architecture, delays are determined by each mix node (not by a packet sender).
# But, for the consistency with Nym's Sphinx implementation, keep the delay field in the Sphinx header.
DELAY_LENGTH = 8
DELAY = b"\x00\x00\x00\x00\x00\x00\x00\x00"
