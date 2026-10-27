import asyncio
import threading
import time
from typing import cast

import pytest
from pwdlib import PasswordHash

from fanfan.adapters.auth.password_hasher import (
    MAX_CONCURRENT_HASHES,
    PwdlibPasswordHasher,
)

pytestmark = pytest.mark.asyncio


class CountingHash:
    """Stands in for pwdlib and records how many calls overlap in threads."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.in_flight = 0
        self.peak_in_flight = 0

    def _work(self) -> None:
        with self._lock:
            self.in_flight += 1
            self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        time.sleep(0.01)
        with self._lock:
            self.in_flight -= 1

    def hash(self, password: str) -> str:
        self._work()
        return f"hashed:{password}"

    def verify(self, password: str, hashed_password: str) -> bool:
        self._work()
        return hashed_password == f"hashed:{password}"


async def test_concurrent_calls_never_exceed_the_memory_bound() -> None:
    hasher = PwdlibPasswordHasher()
    counting = CountingHash()
    hasher._password_hash = cast("PasswordHash", counting)

    results = await asyncio.gather(
        *(hasher.verify("pw", "hashed:pw") for _ in range(5)),
        *(hasher.hash("pw") for _ in range(5)),
    )

    assert counting.peak_in_flight == MAX_CONCURRENT_HASHES
    assert results[:5] == [True] * 5
    assert results[5:] == ["hashed:pw"] * 5


async def test_round_trips_through_real_argon2() -> None:
    hasher = PwdlibPasswordHasher()

    hashed = await hasher.hash("secret")

    assert await hasher.verify("secret", hashed)
    assert not await hasher.verify("wrong", hashed)
