import asyncio

from procrastinate import App

from fanfan.adapters.config.parsers import get_config
from fanfan.adapters.db.event_loop import loop_factory
from fanfan.adapters.procrastinate.pool import create_job_pool
from fanfan.main.common import init
from fanfan.main.di import create_system_container
from fanfan.presentation.worker.middleware import sentry_middleware
from fanfan.presentation.worker.subscriber import CONTAINER_CONTEXT_KEY

# Procrastinate's own queries (fetch, finish, retry) run between jobs, never
# for their whole length, so a few connections serve any concurrency.
JOB_POOL_MAX_SIZE = 3

# On SIGTERM the worker stops fetching and waits this long for running jobs,
# then aborts the rest, which the retry strategy queues again. It must end
# inside Docker's 10 s stop_grace_period, or the SIGKILL that follows leaves
# the jobs "doing" until the stalled-job sweep (routes/maintenance.py).
SHUTDOWN_GRACEFUL_TIMEOUT_SECONDS = 7.0


async def run() -> None:
    config = get_config()
    container = create_system_container()
    pool = create_job_pool(config.db, max_size=JOB_POOL_MAX_SIZE)
    try:
        await pool.open(wait=True)
        procrastinate_app = await container.get(App)
        await procrastinate_app.open_async(pool)
        # Installs its own SIGINT/SIGTERM handlers and returns once shut down.
        await procrastinate_app.run_worker_async(
            concurrency=config.worker.concurrency,
            additional_context={CONTAINER_CONTEXT_KEY: container},
            worker_middleware=[sentry_middleware],
            shutdown_graceful_timeout=SHUTDOWN_GRACEFUL_TIMEOUT_SECONDS,
        )
    finally:
        await pool.close()
        await container.close()


def main() -> None:
    init(service_name="worker")
    asyncio.run(run(), loop_factory=loop_factory())


if __name__ == "__main__":
    main()
