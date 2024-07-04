from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Coroutine

from mixnet.framework import framework


class Framework(framework.Framework):
    def __init__(self):
        super().__init__()

    def queue(self) -> framework.Queue:
        return Queue()

    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)

    def now(self) -> float:
        return time.time()

    def spawn(
        self, coroutine: Coroutine[Any, Any, framework.RT]
    ) -> Awaitable[framework.RT]:
        return asyncio.create_task(coroutine)


class Queue(framework.Queue):
    _queue: asyncio.Queue[bytes]

    def __init__(self):
        super().__init__()
        self._queue = asyncio.Queue()

    async def put(self, data: bytes) -> None:
        await self._queue.put(data)

    async def get(self) -> bytes:
        return await self._queue.get()

    def empty(self) -> bool:
        return self._queue.empty()
