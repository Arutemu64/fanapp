import asyncio
import contextlib
import logging
import signal

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dishka import AsyncContainer

from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.db.outbox_signal import OUTBOX_CHANNEL, PostgresOutboxSignal
from fanfan.application.interactors.outbox.publish_outbox_events import (
    PublishOutboxEvents,
)
from fanfan.application.ports.outbox_signal import OutboxSignal
from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.scheduler.jobs import get_job_definitions, make_interactor_job

logger = logging.getLogger(__name__)


async def _run_outbox_relay(
    container: AsyncContainer,
    outbox_signal: OutboxSignal,
    poll_interval: float,
    stop_event: asyncio.Event,
) -> None:
    """Drain the outbox on every NOTIFY, and at least once per poll interval.

    ``arm()`` before each drain so a NOTIFY that arrives mid-drain wakes the
    next ``wait`` instead of being lost between the drain and the wait; the poll
    interval is the backstop that bounds latency if a signal is ever missed. A
    fresh REQUEST scope per tick mirrors the cron jobs (see scheduler/jobs).
    """
    while not stop_event.is_set():
        outbox_signal.arm()
        try:
            async with container() as request_container:
                relay = await request_container.get(PublishOutboxEvents)
                await relay()
        except Exception:
            # One bad tick must not kill the loop; report it and let the next
            # tick (poll backstop) retry the still-unpublished rows.
            logger.exception("Outbox relay tick failed")
            sentry_sdk.capture_exception()
        await outbox_signal.wait(poll_interval)


async def run() -> None:
    config = get_config()
    container = create_system_container()
    scheduler = AsyncIOScheduler(timezone=config.timezone)

    for job in get_job_definitions(config.scheduler):
        if job.cron is None:
            logger.info("Job '%s' disabled (no cron configured)", job.id)
            continue
        scheduler.add_job(
            make_interactor_job(container, job.interactor),
            CronTrigger.from_crontab(job.cron, timezone=config.timezone),
            id=job.id,
            replace_existing=True,
        )
        logger.info("Job '%s' scheduled (cron: %s)", job.id, job.cron)

    scheduler.start()

    # Outbox relay: not an APScheduler job but a dedicated loop, because it is
    # driven by a Postgres NOTIFY (fired by the outbox INSERT trigger) rather
    # than a fixed clock — the poll interval only bounds worst-case latency when
    # a notification is missed.
    outbox_signal = PostgresOutboxSignal(config.db)
    await outbox_signal.start()
    stop_event = asyncio.Event()
    relay_task = asyncio.create_task(
        _run_outbox_relay(
            container,
            outbox_signal,
            config.outbox.poll_interval_seconds,
            stop_event,
        ),
        name="outbox-relay",
    )
    logger.info(
        "Outbox relay started (NOTIFY on '%s', poll backstop: %ss)",
        OUTBOX_CHANNEL,
        config.outbox.poll_interval_seconds,
    )

    # Block until SIGINT/SIGTERM, then shut down cleanly.
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # add_signal_handler is unsupported on Windows (local dev only).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        relay_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await relay_task
        await outbox_signal.stop()
        scheduler.shutdown()
        await container.close()


def main() -> None:
    init(service_name="scheduler")
    asyncio.run(run())


if __name__ == "__main__":
    main()
