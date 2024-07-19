import sys
from hashlib import sha256
from random import randint

import dispersal.proto as proto
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
    A class handling Data Availability (DA).

    Runs on a hardcoded port.
    Starts a libp2p node.
    Listens on a handler for receiving data.
    Resends all data it receives to all peers it is connected to
    (therefore assumes connection logic is established elsewhere)

    """

    listen_addr: multiaddr.Multiaddr
    libp2phost: host
    port: int
    node_list: []
    # list of packet hashes it "stores"
    hashes: set()

    @classmethod
    async def new(cls, port, node_list, nursery, shutdown, disperse_send):
        self = cls()
        self.listen_addr = multiaddr.Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")
        self.libp2phost = new_host()
        self.port = port
        self.node_list = node_list
        self.hashes = set()
        nursery.start_soon(self.__run, nursery, shutdown, disperse_send)
        if DEBUG:
            print("DA node at port {} initialized".format(port))

    def get_id(self):
        return self.libp2phost.get_id()

    def net_iface(self):
        return self.libp2phost

    def get_port(self):
        return self.port

    async def __run(self, nursery, shutdown, disperse_send):
        """
        Run the node. Starts libp2p host, and listener for data
        """
        async with self.libp2phost.run(listen_addrs=[self.listen_addr]):
            print("started node at {}...".format(self.listen_addr))

            # handler to run when data is received
            async def stream_handler(stream: INetStream) -> None:
                nursery.start_soon(
                    self.read_data, stream, nursery, shutdown, disperse_send
                )

            # set the above handler
            self.libp2phost.set_stream_handler(PROTOCOL_ID, stream_handler)
            # at this point the node is "initialized" - signal it's "ready"
            self.node_list.append(self)
            # run until we shutdown
            await shutdown.wait()

    async def read_data(
        self, stream: INetStream, nursery, shutdown, disperse_send
    ) -> None:
        """
        We need to wait for incoming data, but also we want to shutdown
        when the test is finished.
        The following code makes sure that both events are listened to
        and the first which occurs is handled.
        """

        first_event = None

        async def select_event(async_fn, cancel_scope):
            nonlocal first_event
            first_event = await async_fn()
            cancel_scope.cancel()
            disperse_send.close()

        async def read_stream():
            while True:
                read_bytes = await stream.read(MAX_READ_LEN)
                if read_bytes is not None:
                    message = proto.unpack_from_bytes(read_bytes)
                    hashstr = sha256(message.dispersal_req.blob.data).hexdigest()
                    if hashstr not in self.hashes:
                        # "store" the received packet
                        self.hashes.add(hashstr)
                        # now disperse this hash to all peers
                        nursery.start_soon(self.disperse, read_bytes, disperse_send)
                        if DEBUG:
                            print(
                                "{} stored {}".format(
                                    self.libp2phost.get_id().pretty(), hashstr
                                )
                            )
                    await disperse_send.send(-1)
                else:
                    print("read_bytes is None, unexpected!")

        nursery.start_soon(select_event, read_stream, nursery.cancel_scope)
        nursery.start_soon(select_event, shutdown.wait, nursery.cancel_scope)

    async def disperse(self, packet, disperse_send) -> None:
        # disperse the given packet to all peers
        for p_id in self.libp2phost.get_peerstore().peer_ids():
            if p_id == self.libp2phost.get_id():
                continue
            await disperse_send.send(1)
            stream = await self.libp2phost.new_stream(p_id, [PROTOCOL_ID])

            await stream.write(packet)

    async def has_hash(self, hashstr: str):
        return hashstr in self.hashes
