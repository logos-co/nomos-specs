import abc

from mixnet.framework.framework import Framework


class SimplexConnection(abc.ABC):
    @abc.abstractmethod
    async def send(self, data: bytes) -> None:
        pass

    @abc.abstractmethod
    async def recv(self) -> bytes:
        pass


class LocalSimplexConnection(SimplexConnection):
    def __init__(self, framework: Framework):
        self.queue = framework.queue()

    async def send(self, data: bytes) -> None:
        await self.queue.put(data)

    async def recv(self) -> bytes:
        return await self.queue.get()
