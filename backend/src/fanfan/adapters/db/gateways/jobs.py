from datetime import timedelta
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import JobORM
from fanfan.application.dto.jobs import Job, JobStatus
from fanfan.application.ports.gateways.jobs import JobGateway

# Bound the stored error text: an exception can carry a whole payload in its
# message, and last_error is a debugging aid, not an archive.
_LAST_ERROR_MAX_CHARS = 2000


def _truncate(error: str | None) -> str | None:
    if error is None:
        return None
    return error[:_LAST_ERROR_MAX_CHARS]


class SqlJobGateway(JobGateway):
    # Every time below is the database clock (func.now()), never the worker's,
    # so a worker host's clock skew cannot shift a lease or a retry.

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def claim(self, limit: int, lease: timedelta) -> list[Job]:
        due = (
            select(JobORM.id)
            .where(JobORM.status == JobStatus.PENDING, JobORM.run_at <= func.now())
            # created_at is the transaction timestamp, so every job from one
            # commit ties on it; the uuid7 id breaks the tie in creation order.
            .order_by(JobORM.run_at, JobORM.created_at, JobORM.id)
            .limit(limit)
            # SKIP LOCKED: a concurrent claim skips rows another one is taking
            # instead of blocking on them, so no job is handed out twice.
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        rows = await self.session.scalars(
            update(JobORM)
            .where(JobORM.id.in_(due))
            .values(attempts=JobORM.attempts + 1, run_at=func.now() + lease)
            .returning(JobORM)
        )
        jobs = [Job.model_validate(row) for row in rows]
        # UPDATE ... RETURNING comes back in no particular order.
        jobs.sort(key=lambda job: (job.created_at, job.id))
        return jobs

    async def extend_leases(self, attempts: dict[UUID, int], lease: timedelta) -> None:
        if not attempts:
            return
        current_attempt = or_(
            *(
                and_(JobORM.id == job_id, JobORM.attempts == attempt)
                for job_id, attempt in attempts.items()
            )
        )
        await self.session.execute(
            update(JobORM)
            .where(current_attempt, JobORM.status == JobStatus.PENDING)
            .values(run_at=func.now() + lease)
        )

    async def finish(
        self, job_id: UUID, attempt: int, status: JobStatus, error: str | None
    ) -> None:
        values: dict[str, Any] = {"status": status, "finished_at": func.now()}
        # A job done on a retry keeps the error of the attempt before it.
        if error is not None:
            values["last_error"] = _truncate(error)
        await self.session.execute(
            update(JobORM)
            .where(
                JobORM.id == job_id,
                JobORM.attempts == attempt,
                JobORM.status == JobStatus.PENDING,
            )
            .values(**values)
        )

    async def reschedule(
        self, job_id: UUID, attempt: int, delay: timedelta, error: str
    ) -> None:
        await self.session.execute(
            update(JobORM)
            .where(
                JobORM.id == job_id,
                JobORM.attempts == attempt,
                JobORM.status == JobStatus.PENDING,
            )
            .values(run_at=func.now() + delay, last_error=_truncate(error))
        )

    async def seconds_until_next_due(self) -> float | None:
        next_run_at = select(func.min(JobORM.run_at)).where(
            JobORM.status == JobStatus.PENDING
        )
        seconds = await self.session.scalar(
            select(func.extract("epoch", next_run_at.scalar_subquery() - func.now()))
        )
        if seconds is None:
            return None
        return float(seconds)

    async def delete_finished_before(self, days: int) -> int:
        cutoff = func.now() - timedelta(days=days)
        result = await self.session.execute(
            delete(JobORM).where(
                JobORM.finished_at.is_not(None),
                JobORM.finished_at < cutoff,
            )
        )
        # execute() is typed as Result, but a DELETE yields a CursorResult.
        return cast("CursorResult[Any]", result).rowcount
