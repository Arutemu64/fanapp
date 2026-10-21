import asyncio
import contextlib
import logging
import signal

from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.db.event_loop import loop_factory
from fanfan.adapters.db.job_signal import JOBS_CHANNEL, PostgresJobSignal
from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.worker.routes import setup_router
from fanfan.presentation.worker.worker import JobWorker

logger = logging.getLogger(__name__)


async def run() -> None:
    config = get_config()
    container = create_system_container()
    job_signal = PostgresJobSignal(config.db)
    await job_signal.start()
    worker = JobWorker(
        container=container,
        router=setup_router(),
        signal=job_signal,
        config=config.jobs,
    )

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        # add_signal_handler is unsupported on Windows (local dev only).
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop_event.set)

    logger.info(
        "Job worker started (NOTIFY on '%s', concurrency: %s, poll backstop: %ss)",
        JOBS_CHANNEL,
        config.jobs.concurrency,
        config.jobs.poll_interval_seconds,
    )
    try:
        await worker.run(stop_event)
    finally:
        await job_signal.stop()
        await container.close()


def main() -> None:
    init(service_name="worker")
    asyncio.run(run(), loop_factory=loop_factory())


if __name__ == "__main__":
    main()
