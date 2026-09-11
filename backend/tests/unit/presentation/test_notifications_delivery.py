import asyncio
import logging

import pytest

from fanfan.core.exceptions.notifications import UserNotReachable
from fanfan.core.vo.notification import generate_notification_id
from fanfan.presentation.faststream.routes import notifications as routes

pytestmark = pytest.mark.unit


class _FakeMessage:
    """Records the JetStream ack calls _deliver_to_channel makes."""

    def __init__(self) -> None:
        self.in_progress_calls = 0
        self.acked = False
        self.rejected = False
        self.nack_delay: int | None = None

    async def in_progress(self) -> None:
        self.in_progress_calls += 1

    async def ack(self) -> None:
        self.acked = True

    async def reject(self) -> None:
        self.rejected = True

    async def nack(self, delay: int | None = None) -> None:
        self.nack_delay = delay


async def _deliver(send, msg: _FakeMessage) -> None:
    await routes._deliver_to_channel(
        channel="push",
        notification_id=generate_notification_id(),
        send=send,
        msg=msg,
        logger=logging.getLogger("test"),
    )


async def test_heartbeat_pings_while_send_runs_then_stops(monkeypatch) -> None:
    # A send that outlasts several ping intervals must be kept in-progress, so
    # JetStream does not redeliver from under the still-running handler.
    monkeypatch.setattr(routes, "_IN_PROGRESS_INTERVAL_SECONDS", 0.01)
    msg = _FakeMessage()

    async def slow_send(_input) -> None:
        await asyncio.sleep(0.05)

    await _deliver(slow_send, msg)

    assert msg.in_progress_calls >= 1
    assert msg.acked

    # The heartbeat is cancelled the moment the send settles: no pings after.
    settled_count = msg.in_progress_calls
    await asyncio.sleep(0.03)
    assert msg.in_progress_calls == settled_count


async def test_heartbeat_cancelled_on_exception_path(monkeypatch) -> None:
    # The heartbeat must also stop when the send raises and the message is
    # rejected — a leaked task would keep pinging a settled message forever.
    monkeypatch.setattr(routes, "_IN_PROGRESS_INTERVAL_SECONDS", 0.01)
    msg = _FakeMessage()

    async def failing_send(_input) -> None:
        await asyncio.sleep(0.03)
        raise UserNotReachable

    await _deliver(failing_send, msg)

    assert msg.rejected
    settled_count = msg.in_progress_calls
    await asyncio.sleep(0.03)
    assert msg.in_progress_calls == settled_count
