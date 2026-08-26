import asyncio

import pytest

from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.outbox_signal import PostgresOutboxSignal

pytestmark = pytest.mark.asyncio


def _signal() -> PostgresOutboxSignal:
    # No connection is opened (start() is never called); these tests drive the
    # in-process latch directly to pin its edge-triggered semantics.
    config = DatabaseConfig(url="postgresql+asyncpg://u:p@localhost:5432/db")
    return PostgresOutboxSignal(config)


def _notify(signal: PostgresOutboxSignal) -> None:
    # Stand in for asyncpg delivering a NOTIFY on the listen connection.
    signal._on_notify(object(), 0, "outbox_new", "")


async def test_wait_returns_immediately_after_a_signal():
    signal = _signal()
    signal.arm()
    _notify(signal)

    # A generous timeout would be returned in full if the signal were missed;
    # the outer wait_for fails the test instead of hanging if it is.
    await asyncio.wait_for(signal.wait(60), timeout=1)


async def test_wait_times_out_when_no_signal_arrives():
    signal = _signal()
    signal.arm()

    loop = asyncio.get_running_loop()
    start = loop.time()
    await signal.wait(0.05)
    # It waited out the backstop interval rather than returning early.
    assert loop.time() - start >= 0.05


async def test_arm_clears_a_prior_signal():
    signal = _signal()
    _notify(signal)  # a signal lands...
    signal.arm()  # ...but arm() before the next drain clears it

    loop = asyncio.get_running_loop()
    start = loop.time()
    await signal.wait(0.05)
    # The stale signal was cleared, so the next wait blocks for the full backstop.
    assert loop.time() - start >= 0.05


async def test_signal_arriving_during_a_drain_is_not_lost():
    signal = _signal()
    # The relay arms, then drains; a NOTIFY that lands between the arm and the
    # following wait must still wake that wait rather than being swallowed.
    signal.arm()
    _notify(signal)

    await asyncio.wait_for(signal.wait(60), timeout=1)
