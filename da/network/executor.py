from hashlib import sha256
from random import randbytes
from typing import Self

import dispersal.proto as proto
import multiaddr
import trio
from constants import HASH_LENGTH, PROTOCOL_ID
from libp2p import host, new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr


class Executor:
    """
    A class for simulating a simple executor.

    Runs on hardcoded port.
    Creates random data and disperses it.
    One packet represents a subnet, and each packet is sent
    to one DANode.

    """

    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    num_subnets: int
    node_list: {}
    # size of a packet
    data_size: int
    # holds random data for dispersal
    data: []
    # stores hashes of the data for later verification
    data_hashes: []
    blob_id: int

    @classmethod
    def new(cls, port, node_list, num_subnets, data_size) -> Self:
        self = cls()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        self.num_subnets = num_subnets
        self.data_size = data_size
        # one packet per subnet
        self.data = [[] * data_size] * num_subnets
        # one hash per packet. **assumes 256 hash length**
        self.data_hashes = [[] * HASH_LENGTH] * num_subnets
        self.node_list = node_list
        # create random simulated data right from the beginning
        self.__create_data()
        return self

    def get_id(self):
        return self.host.get_id()

    def net_iface(self):
        return self.host

    def get_port(self):
        return self.port

    def get_hash(self, index: int):
        return self.data_hashes[index]

    def __create_data(self):
        """
        Create random data for dispersal
        One packet of self.data_size length per subnet
        """
        id = sha256()
        for i in range(self.num_subnets):
            self.data[i] = randbytes(self.data_size)
            self.data_hashes[i] = sha256(self.data[i]).hexdigest()
            id.update(self.data[i])
        self.blob_id = id.digest()

    async def disperse(self, nursery):
        """
        Disperse the data to the DA network.
        Sends one packet of data per network node
        """

        async with self.host.run(listen_addrs=[self.listen_addr]):
            for subnet, nodes in self.node_list.items():
                # get first node of each subnet
                n = nodes[0]
                # connect to it...
                await self.host.connect(n)

                # ...and send (async)
                stream = await self.host.new_stream(n.peer_id, [PROTOCOL_ID])
                nursery.start_soon(self.write_data, stream, subnet)

    async def write_data(self, stream: INetStream, index: int) -> None:
        """
        Send data to peer (async)
        The index is the subnet number
        """

        blob_id = self.blob_id
        blob_data = self.data[index]

        message = proto.new_dispersal_req_msg(blob_id, blob_data)
        await stream.write(message)
