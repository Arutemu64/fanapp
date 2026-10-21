import logging

from dishka import AsyncContainer
from procrastinate import Blueprint, JobContext

from fanfan.presentation.worker.config import WorkerConfig
from fanfan.presentation.worker.subscriber import CONTAINER_CONTEXT_KEY

logger = logging.getLogger(__name__)

maintenance_tasks = Blueprint()


# A job whose worker died (SIGKILL, OOM, a lost host) stays in "doing" forever:
# Procrastinate detects it by the worker's missing heartbeat but leaves the
# retry to the app, with this periodic task as its documented recipe.
# https://procrastinate.readthedocs.io/en/stable/howto/production/retry_stalled_jobs.html
# The queueing lock keeps one run queued at a time if the worker falls behind.
# Every periodic task is called with its scheduled `timestamp`, used or not.
@maintenance_tasks.periodic(cron="*/5 * * * *", periodic_id="retry_stalled_jobs")
@maintenance_tasks.task(
    name="retry_stalled_jobs", queueing_lock="retry_stalled_jobs", pass_context=True
)
async def retry_stalled_jobs(context: JobContext, timestamp: int) -> None:
    job_manager = context.app.job_manager
    for job in await job_manager.get_stalled_jobs():
        logger.warning(
            "Retrying a stalled job",
            extra={"job_id": job.id, "task_name": job.task_name},
        )
        await job_manager.retry_job(job)


# Finished jobs are kept a while for inspection, then deleted, so the jobs and
# events tables stay small. Procrastinate's builtin remove_old_jobs cannot be
# made periodic as is: a periodic task is called with a `timestamp` argument it
# does not accept.
@maintenance_tasks.periodic(cron="17 3 * * *", periodic_id="prune_finished_jobs")
@maintenance_tasks.task(
    name="prune_finished_jobs", queueing_lock="prune_finished_jobs", pass_context=True
)
async def prune_finished_jobs(context: JobContext, timestamp: int) -> None:
    container: AsyncContainer = context.additional_context[CONTAINER_CONTEXT_KEY]
    config = await container.get(WorkerConfig)
    await context.app.job_manager.delete_old_jobs(
        nb_hours=config.job_retention_days * 24,
        include_failed=True,
        include_cancelled=True,
        include_aborted=True,
    )
