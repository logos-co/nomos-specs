import sys
from hashlib import sha256
from random import randint

import multiaddr
import trio
from blspy import BasicSchemeMPL, G1Element, PrivateKey
from libp2p import host, new_host
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.typing import TProtocol

PROTOCOL_ID = TProtocol("/nomosda/1.0.0")
MAX_READ_LEN = 2**32 - 1


class DANode:
    """
    A class handling Data Availability (DA)

    """

    pk: PrivateKey
    id: G1Element
    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    node_list: []
    data: []
    hash: str
    # inbound_socket: asyncio.Queue
    # outbound_socket: asyncio.Queue

    @classmethod
    async def new(cls, port, node_list, nursery):
        self = cls()
        # self.pk = generate_random_sk()
        # self.id = self.pk.get_g1()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        self.node_list = node_list
        self.data = []
        self.hash = ""
        nursery.start_soon(self.__run, nursery)
        print("DA node at port {} initialized".format(port))
        # self.inbound_socket = asyncio.Queue()
        # self.outbound_socket = asyncio.Queue()

    def hex_id(self):
        return bytes(self.id).hex()

    def get_id(self):
        return self.host.get_id()

    def net_iface(self):
        return self.host

    def get_port(self):
        return self.port

    async def __run(self, nursery):
        """ """
        async with self.host.run(listen_addrs=[self.listen_addr]):
            print("starting node at {}...".format(self.listen_addr))

            async def stream_handler(stream: INetStream) -> None:
                nursery.start_soon(self.read_data, stream)
                nursery.start_soon(self.write_data, stream)

            self.host.set_stream_handler(PROTOCOL_ID, stream_handler)
            self.node_list.append(self)
            await trio.sleep_forever()

    async def read_data(self, stream: INetStream) -> None:
        while True:
            read_bytes = await stream.read(MAX_READ_LEN)
            if read_bytes is not None:
                self.data = read_bytes
                self.hash = sha256(self.data).hexdigest()
                print("{} stored {}".format(self.host.get_id().pretty(), self.hash))
            else:
                print("read_bytes is None, unexpected!")

    async def write_data(self, stream: INetStream) -> None:
        async_f = trio.wrap_file(sys.stdin)
        while True:
            line = await async_f.readline()
            await stream.write(line.encode())


def generate_random_sk() -> PrivateKey:
    seed = bytes([randint(0, 255) for _ in range(32)])
    return BasicSchemeMPL.key_gen(seed)
