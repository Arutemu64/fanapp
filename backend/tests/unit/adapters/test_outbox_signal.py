import asyncio
from collections.abc import Callable
from typing import Any, cast

import pytest

from fanfan.adapters.db import outbox_signal
from fanfan.adapters.db.config import DatabaseConfig
from fanfan.adapters.db.outbox_signal import PostgresOutboxSignal

pytestmark = pytest.mark.asyncio


def _signal() -> PostgresOutboxSignal:
    # No connection is opened (start() is never called); these tests drive the
    # in-process latch directly to pin its edge-triggered semantics.
    config = DatabaseConfig(url="postgresql+asyncpg://u:p@localhost:5432/db")
    return PostgresOutboxSignal(config)


def _notify(signal: PostgresOutboxSignal) -> None:
    signal._on_notify(object(), 0, "outbox_new", "")


async def test_wait_returns_immediately_after_a_signal() -> None:
    signal = _signal()
    signal.arm()
    _notify(signal)

    # A generous timeout would be returned in full if the signal were missed;
    # the outer wait_for fails the test instead of hanging if it is.
    await asyncio.wait_for(signal.wait(60), timeout=1)


async def test_wait_times_out_when_no_signal_arrives() -> None:
    signal = _signal()
    signal.arm()

    loop = asyncio.get_running_loop()
    start = loop.time()
    await signal.wait(0.05)
    # It waited out the backstop interval rather than returning early.
    assert loop.time() - start >= 0.05


async def test_arm_clears_a_prior_signal() -> None:
    signal = _signal()
    _notify(signal)  # a signal lands...
    signal.arm()  # ...but arm() before the next drain clears it

    loop = asyncio.get_running_loop()
    start = loop.time()
    await signal.wait(0.05)
    # The stale signal was cleared, so the next wait blocks for the full backstop.
    assert loop.time() - start >= 0.05


async def test_signal_arriving_during_a_drain_is_not_lost() -> None:
    signal = _signal()
    # The relay arms, then drains; a NOTIFY that lands between the arm and the
    # following wait must still wake that wait rather than being swallowed.
    signal.arm()
    _notify(signal)

    await asyncio.wait_for(signal.wait(60), timeout=1)


class _FakeListenConnection:
    """Stands in for the LISTEN connection in _hold: termination and probe
    behaviour are driven by the test instead of a real socket."""

    def __init__(self, *, probe_hangs: bool) -> None:
        self.probe_hangs = probe_hangs
        self.probes = 0
        self.probed_twice = asyncio.Event()
        self.on_terminate: Callable[[object], None] | None = None

    def add_termination_listener(self, callback: Callable[[object], None]) -> None:
        self.on_terminate = callback

    async def fetchval(self, _query: str) -> int:
        self.probes += 1
        if self.probes >= 2:
            self.probed_twice.set()
        if self.probe_hangs:
            # A half-dead socket: the query never gets an answer.
            await asyncio.Event().wait()
        return 1


@pytest.fixture
def fast_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(outbox_signal, "_HEALTH_CHECK_INTERVAL_SECONDS", 0.01)
    monkeypatch.setattr(outbox_signal, "_HEALTH_CHECK_TIMEOUT_SECONDS", 0.05)


@pytest.mark.usefixtures("fast_probe")
async def test_hold_raises_when_the_connection_silently_stops_answering() -> None:
    # No termination callback ever fires, as with a NAT/firewall drop; the probe
    # timing out is the only way the supervisor learns it must reconnect.
    connection = _FakeListenConnection(probe_hangs=True)

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(_signal()._hold(cast("Any", connection)), timeout=1)


@pytest.mark.usefixtures("fast_probe")
async def test_hold_keeps_probing_a_healthy_connection_until_it_drops() -> None:
    connection = _FakeListenConnection(probe_hangs=False)
    hold = asyncio.create_task(_signal()._hold(cast("Any", connection)))

    await asyncio.wait_for(connection.probed_twice.wait(), timeout=1)
    assert not hold.done()

    assert connection.on_terminate is not None
    connection.on_terminate(connection)
    await asyncio.wait_for(hold, timeout=1)


async def test_reconnect_delay_backs_off_to_the_cap() -> None:
    first = outbox_signal._reconnect_delay(1)
    assert 0.5 <= first <= 1.5
    # Far past the cap, and past where an unclamped power would overflow float.
    for failures in (10, 5000):
        delay = outbox_signal._reconnect_delay(failures)
        assert delay == outbox_signal._RECONNECT_MAX_DELAY_SECONDS
