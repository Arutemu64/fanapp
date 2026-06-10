import asyncio
import contextlib
import logging
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from fanfan.adapters.config.parsers import get_config
from fanfan.application.interactors.outbox.publish_outbox_events import (
    PublishOutboxEvents,
)
from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.scheduler.jobs import get_job_definitions, make_interactor_job

logger = logging.getLogger(__name__)


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

    # Outbox relay: an interval (not cron) job so delivery latency is seconds,
    # not minutes. max_instances/coalesce stop a slow tick piling up on itself.
    scheduler.add_job(
        make_interactor_job(container, PublishOutboxEvents),
        IntervalTrigger(seconds=config.outbox.poll_interval_seconds),
        id="outbox_relay",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    logger.info(
        "Job 'outbox_relay' scheduled (interval: %ss)",
        config.outbox.poll_interval_seconds,
    )

    scheduler.start()

    # Block until SIGINT/SIGTERM, then shut down cleanly.
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # add_signal_handler is unsupported on Windows (local dev only).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    try:
        await stop_event.wait()
    finally:
        scheduler.shutdown()
        await container.close()


def main() -> None:
    init(service_name="scheduler")
    asyncio.run(run())


if __name__ == "__main__":
    main()
