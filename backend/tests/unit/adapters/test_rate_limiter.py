import asyncio
import itertools

import pytest

from fanfan.adapters.rate_limiter import RateLimiter

pytestmark = pytest.mark.unit


async def test_concurrent_callers_are_spaced_by_the_rate() -> None:
    limiter = RateLimiter(per_second=50)
    loop = asyncio.get_running_loop()
    started: list[float] = []

    async def call() -> None:
        await limiter.wait()
        started.append(loop.time())

    await asyncio.gather(*(call() for _ in range(5)))

    started.sort()
    gaps = [later - earlier for earlier, later in itertools.pairwise(started)]
    # 1/50 s apart, allowing for timer slack on a busy runner.
    assert all(gap >= 0.015 for gap in gaps)


async def test_first_call_after_an_idle_spell_does_not_wait() -> None:
    limiter = RateLimiter(per_second=1)
    loop = asyncio.get_running_loop()

    before = loop.time()
    await limiter.wait()

    assert loop.time() - before < 0.1
