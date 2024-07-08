import sys
from hashlib import sha256
from random import randint

import multiaddr
import trio
from blspy import BasicSchemeMPL, G1Element, PrivateKey
from constants import *
from libp2p import host, new_host
from libp2p.network.stream.exceptions import StreamReset
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.peerinfo import info_from_p2p_addr


class DANode:
    """
    A class handling Data Availability (DA)

    """

    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    node_list: []
    hashes: set()

    @classmethod
    async def new(cls, port, node_list, nursery, shutdown):
        self = cls()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        self.node_list = node_list
        self.hashes = set()
        nursery.start_soon(self.__run, nursery, shutdown)
        print("DA node at port {} initialized".format(port))

    def get_id(self):
        return self.host.get_id()

    def net_iface(self):
        return self.host

    def get_port(self):
        return self.port

    async def __run(self, nursery, shutdown):
        """ """
        async with self.host.run(listen_addrs=[self.listen_addr]):
            print("starting node at {}...".format(self.listen_addr))

            async def stream_handler(stream: INetStream) -> None:
                nursery.start_soon(self.read_data, stream, nursery, shutdown)
                # nursery.start_soon(self.write_data, stream)

            self.host.set_stream_handler(PROTOCOL_ID, stream_handler)
            self.node_list.append(self)
            await shutdown.wait()

    async def read_data(self, stream: INetStream, nursery, shutdown) -> None:
        first_event = None

        async def select_event(async_fn, cancel_scope):
            nonlocal first_event
            first_event = await async_fn()
            cancel_scope.cancel()

        async def read_stream():
            while True:
                read_bytes = await stream.read(MAX_READ_LEN)
                if read_bytes is not None:
                    hashstr = sha256(read_bytes).hexdigest()
                    self.hashes.add(hashstr)
                    print("{} stored {}".format(self.host.get_id().pretty(), hashstr))
                else:
                    print("read_bytes is None, unexpected!")

        nursery.start_soon(select_event, read_stream, nursery.cancel_scope)
        nursery.start_soon(select_event, shutdown.wait, nursery.cancel_scope)

    """
    async def write_data(self, stream: INetStream) -> None:
        async_f = trio.wrap_file(sys.stdin)
        while True:
            line = await async_f.readline()
            await stream.write(line.encode())
    """

    async def has_hash(self, hashstr: str):
        return hashstr in self.hashes
