from __future__ import annotations

import abc
from typing import Any, Awaitable, Coroutine, TypeVar

RT = TypeVar("RT")


class Framework(abc.ABC):
    @abc.abstractmethod
    def queue(self) -> Queue:
        pass

    @abc.abstractmethod
    async def sleep(self, seconds: float) -> None:
        pass

    @abc.abstractmethod
    def now(self) -> float:
        pass

    @abc.abstractmethod
    def spawn(self, coroutine: Coroutine[Any, Any, RT]) -> Awaitable[RT]:
        pass


class Queue(abc.ABC):
    @abc.abstractmethod
    async def put(self, data: bytes) -> None:
        pass

    @abc.abstractmethod
    async def get(self) -> bytes:
        pass

    @abc.abstractmethod
    def empty(self) -> bool:
        pass
