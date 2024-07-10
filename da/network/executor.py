import sys
from hashlib import sha256
from random import randbytes
from typing import Self

import multiaddr
import trio
from constants import *
from libp2p import host, new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr


class Executor:
    """
    A class for simulating a simple executor

    """

    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    num_subnets: int
    data_size: int
    node_list: {}
    data: []
    data_hashes: []

    @classmethod
    def new(cls, port, node_list, num_subnets, data_size) -> Self:
        self = cls()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        self.num_subnets = num_subnets
        self.data_size = data_size
        self.data = [[] * data_size] * num_subnets
        self.data_hashes = [[] * 256] * num_subnets
        self.node_list = node_list
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
        for i in range(self.num_subnets):
            self.data[i] = randbytes(self.data_size)
            self.data_hashes[i] = sha256(self.data[i]).hexdigest()

    async def execute(self, nursery):
        """ """
        async with self.host.run(listen_addrs=[self.listen_addr]):
            for subnet, nodes in self.node_list.items():
                n = nodes[0]
                await self.host.connect(n)

                stream = await self.host.new_stream(n.peer_id, [PROTOCOL_ID])
                nursery.start_soon(self.write_data, stream, subnet)

    async def write_data(self, stream: INetStream, index: int) -> None:
        await stream.write(self.data[index])
