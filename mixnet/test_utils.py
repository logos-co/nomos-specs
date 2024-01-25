import asyncio


def with_test_timeout(t):
    def wrapper(coroutine):
        async def run(*args, **kwargs):
            async with asyncio.timeout(t):
                return await coroutine(*args, **kwargs)

        return run

    return wrapper
