import asyncio
import contextlib
import logging

import sentry_sdk
from dishka import AsyncContainer

from fanfan.application.interactors.outbox.publish_outbox_events import (
    PublishOutboxEvents,
)
from fanfan.application.ports.outbox_signal import OutboxSignal

logger = logging.getLogger(__name__)


class OutboxRelay:
    """Drains the outbox to NATS from a background task of the stream worker.

    Not a subscriber or a scheduled job: it is driven by a Postgres NOTIFY
    (fired by the outbox INSERT trigger, ADR-0015) rather than by a message or a
    clock, so it is a plain asyncio loop the app starts and stops with itself.
    """

    def __init__(
        self,
        container: AsyncContainer,
        outbox_signal: OutboxSignal,
        poll_interval: float,
    ) -> None:
        self._container = container
        self._signal = outbox_signal
        self._poll_interval = poll_interval
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="outbox-relay")
        logger.info(
            "Outbox relay started",
            extra={"poll_interval_seconds": self._poll_interval},
        )

    async def stop(self) -> None:
        if self._task is not None:
            # Cancelling mid-drain rolls the tick's transaction back, so its
            # rows stay unpublished and the next start sends them again; the
            # stream's duplicate window and idempotent consumers absorb a
            # publish that landed before the cancel.
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run(self) -> None:
        """Drain the outbox on every NOTIFY, and at least once per poll interval.

        ``arm()`` before each drain so a NOTIFY that arrives mid-drain wakes the
        next ``wait`` instead of being lost between the drain and the wait; the
        poll interval is the backstop that bounds latency if a signal is ever
        missed. A fresh REQUEST scope per tick, like every consumed message.
        """
        while True:
            self._signal.arm()
            try:
                async with self._container() as request_container:
                    relay = await request_container.get(PublishOutboxEvents)
                    await relay()
            except Exception:
                # One bad tick must not kill the loop; report it and let the
                # next tick (poll backstop) retry the still-unpublished rows.
                logger.exception(
                    "Outbox relay tick failed", extra={"relay_event": "tick_failed"}
                )
                sentry_sdk.capture_exception()
            await self._signal.wait(self._poll_interval)
