import logging
from datetime import timedelta
from uuid import UUID

from fanfan.application.dto.jobs import Job, JobStatus
from fanfan.application.interactors.jobs.config import JobsConfig
from fanfan.application.ports.gateways.jobs import JobGateway
from fanfan.application.ports.uow import UnitOfWork

logger = logging.getLogger(__name__)

# Delay before each retry of a failing job, by attempts so far; the last one
# repeats. A plain immediate retry would loop a job that always fails hot until
# it runs out of attempts.
_RETRY_DELAYS = (
    timedelta(seconds=1),
    timedelta(seconds=5),
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=5),
)


def retry_delay(attempt: int) -> timedelta:
    index = min(attempt, len(_RETRY_DELAYS)) - 1
    return _RETRY_DELAYS[index]


def _describe(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


class JobQueue:
    """The worker's side of the jobs table: claim, renew and settle jobs.

    Each call is its own short transaction, committed before it returns, so no
    lock or connection is held while a job runs. A job's outcome is recorded
    against the attempt that claimed it (see JobGateway).
    """

    def __init__(
        self, job_gateway: JobGateway, uow: UnitOfWork, config: JobsConfig
    ) -> None:
        self.job_gateway = job_gateway
        self.uow = uow
        self.config = config

    @property
    def _lease(self) -> timedelta:
        return timedelta(seconds=self.config.lease_seconds)

    async def claim(self, limit: int) -> list[Job]:
        jobs = await self.job_gateway.claim(limit, self._lease)
        await self.uow.commit()
        return jobs

    async def renew(self, attempts: dict[UUID, int]) -> None:
        if not attempts:
            return
        await self.job_gateway.extend_leases(attempts, self._lease)
        await self.uow.commit()

    async def seconds_until_next_due(self) -> float | None:
        return await self.job_gateway.seconds_until_next_due()

    async def complete(self, job: Job) -> None:
        await self.job_gateway.finish(job.id, job.attempts, JobStatus.DONE, None)
        await self.uow.commit()

    async def discard(self, job: Job, reason: str) -> None:
        await self.job_gateway.finish(job.id, job.attempts, JobStatus.DISCARDED, reason)
        await self.uow.commit()
        logger.info(
            "Job discarded",
            extra={**_job_extra(job), "job_event": "discarded", "reason": reason},
        )

    async def retry_after(self, job: Job, delay: timedelta, reason: str) -> None:
        """Retry the job once ``delay`` has passed, at the handler's request."""
        if await self._give_up_if_exhausted(job, reason):
            return
        await self.job_gateway.reschedule(job.id, job.attempts, delay, reason)
        await self.uow.commit()
        logger.warning(
            "Job asked to be retried later",
            extra={
                **_job_extra(job),
                "job_event": "retry_after",
                "reason": reason,
                "retry_in_seconds": delay.total_seconds(),
            },
        )

    async def fail_attempt(self, job: Job, error: Exception) -> None:
        """Retry the job with backoff after its handler raised ``error``."""
        if await self._give_up_if_exhausted(job, _describe(error), error):
            return
        delay = retry_delay(job.attempts)
        await self.job_gateway.reschedule(job.id, job.attempts, delay, _describe(error))
        await self.uow.commit()
        logger.warning(
            "Job failed; retry scheduled",
            exc_info=error,
            extra={
                **_job_extra(job),
                "job_event": "failed_attempt",
                "retry_in_seconds": delay.total_seconds(),
            },
        )

    async def give_up(
        self, job: Job, reason: str, error: Exception | None = None
    ) -> None:
        """Settle the job as failed without retrying it."""
        await self.job_gateway.finish(job.id, job.attempts, JobStatus.FAILED, reason)
        await self.uow.commit()
        # ERROR, which Sentry captures: the job's work is lost for good.
        logger.error(
            "Job failed for good",
            exc_info=error,
            extra={**_job_extra(job), "job_event": "gave_up", "reason": reason},
        )

    async def _give_up_if_exhausted(
        self, job: Job, reason: str, error: Exception | None = None
    ) -> bool:
        if job.attempts < self.config.max_attempts:
            return False
        await self.give_up(job, reason, error)
        return True


def _job_extra(job: Job) -> dict[str, str | int]:
    return {"job_id": str(job.id), "job_name": job.name, "attempt": job.attempts}
