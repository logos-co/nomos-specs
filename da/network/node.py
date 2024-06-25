import sys
import asyncio
import multiaddr

from typing import Self

from random import randint

from libp2p import new_host, host

from libp2p.network.stream.net_stream_interface import (
    INetStream,
)
from libp2p.peer.peerinfo import (
    info_from_p2p_addr,
)
from libp2p.typing import (
    TProtocol,
)

from blspy import PrivateKey, BasicSchemeMPL, G1Element

PROTOCOL_ID = TProtocol("/nomosda/1.0.0")
MAX_READ_LEN = 2 ^ 32 - 1


class DANode:
    """
    A class handling Data Availability (DA)

    """

    pk: PrivateKey
    task: asyncio.Task  # A reference just to prevent task from being garbage collected
    id: G1Element
    listen_addr: multiaddr.Multiaddr
    host: host
    port: int
    #inbound_socket: asyncio.Queue
    #outbound_socket: asyncio.Queue

    @classmethod
    async def new(cls, port) -> Self:
        self = cls()
        self.pk = generate_random_sk()
        self.id = self.pk.get_g1()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.host = new_host()
        self.port = port
        #self.inbound_socket = asyncio.Queue()
        #self.outbound_socket = asyncio.Queue()
        loop =  asyncio.get_running_loop()
        self.task = await loop.create_task(self.__run())
        return self

    def hex_id(self):
        return bytes(self.id).hex()

    async def __run(self):
        """
        self.tasks.add(self.task)
        # To discard the task from the set automatically when it is done.
        self.task.add_done_callback(self.tasks.discard)
        """
        async with self.host.run(listen_addrs=[self.listen_addr]), asyncio.get_running_loop() as tg:
            print("starting node at {self.listen_addr}...")

            async def stream_handler(self, stream: INetStream) -> None:
                tg.create_task(self.read_data(stream))
                tg.create_task(self.write_data(stream))

            self.host.set_stream_handler(PROTOCOL_ID, stream_handler)

    async def read_data(self, stream: INetStream) -> None:
        while True:
            read_bytes = await stream.read(MAX_READ_LEN)
            if read_bytes is not None:
                read_string = read_bytes.decode()
                if read_string != "\n":
                    # Green console colour: \x1b[32m
                    # Reset console colour: \x1b[0m
                    print("\x1b[32m %s\x1b[0m " % read_string, end="")

    async def write_data(self, stream: INetStream) -> None:
        loop = asyncio.get_event_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        while True:
            line = await reader.readline()
            await stream.write(line.encode())


def generate_random_sk() -> PrivateKey:
    seed = bytes([randint(0, 255) for _ in range(32)])
    return BasicSchemeMPL.key_gen(seed)
