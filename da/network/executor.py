import sys
from hashlib import sha256
from random import randbytes
from typing import Self

import multiaddr
import trio
from libp2p import host, new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.typing import TProtocol

PROTOCOL_ID = TProtocol("/nomosda/1.0.0")
MAX_READ_LEN = 2**32 - 1
# make this ocnfigurable
DATA_SIZE = 1024
# make this ocnfigurable
COL_SIZE = 4096


class Executor:
    """
    A class for simulating a simple executor

    """

    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    node_list: []
    data: []
    data_hashes: []

    @classmethod
    def new(cls, port, node_list) -> Self:
        self = cls()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        self.data = [[] * DATA_SIZE] * COL_SIZE
        self.data_hashes = [[] * 256] * COL_SIZE
        self.node_list = node_list
        self.__create_data()
        return self

    def get_id(self):
        return self.host.get_id()

    def net_iface(self):
        return self.host

    def get_port(self):
        return self.port

    def __create_data(self):
        for i in range(COL_SIZE):
            self.data[i] = randbytes(DATA_SIZE)
            self.data_hashes[i] = sha256(self.data[i]).hexdigest()

    async def execute(self, nursery):
        """ """
        async with self.host.run(listen_addrs=[self.listen_addr]):
            for i, n in enumerate(self.node_list):
                await self.host.connect(n)

                stream = await self.host.new_stream(n.peer_id, [PROTOCOL_ID])
                nursery.start_soon(self.write_data, stream, i)

    async def write_data(self, stream: INetStream, index: int) -> None:
        await stream.write(self.data[index])
