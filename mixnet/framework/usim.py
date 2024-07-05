from typing import Any, Awaitable, Coroutine

import usim

from mixnet.framework import framework


class Framework(framework.Framework):
    _scope: usim.Scope

    def __init__(self, scope: usim.Scope) -> None:
        super().__init__()
        self._scope = scope

    def queue(self) -> framework.Queue:
        return Queue()

    async def sleep(self, seconds: float) -> None:
        await (usim.time + seconds)

    def now(self) -> float:
        # round to milliseconds to make analysis not too heavy
        return int(usim.time.now * 1000) / 1000

    def spawn(
        self, coroutine: Coroutine[Any, Any, framework.RT]
    ) -> Awaitable[framework.RT]:
        return self._scope.do(coroutine)


class Queue(framework.Queue):
    _queue: usim.Queue[bytes]

    def __init__(self):
        super().__init__()
        self._queue = usim.Queue()

    async def put(self, data: bytes) -> None:
        await self._queue.put(data)

    async def get(self) -> bytes:
        return await self._queue

    def empty(self) -> bool:
        return len(self._queue._buffer) == 0
