from datetime import timedelta
from typing import Protocol
from uuid import UUID

from fanfan.application.dto.jobs import Job, JobStatus


class JobGateway(Protocol):
    """The jobs table, worked as a queue.

    A pending job runs once its ``run_at`` has passed. Claiming a job pushes
    ``run_at`` a lease ahead, so the claim needs no lock held while the job
    runs: a worker that dies simply stops renewing, and the job comes due again.
    Every write after the claim names the attempt it belongs to, so a worker
    whose lease lapsed cannot settle a job someone else has since reclaimed.
    """

    async def claim(self, limit: int, lease: timedelta) -> list[Job]:
        """Take up to ``limit`` due jobs, oldest first, and count an attempt.

        FOR UPDATE SKIP LOCKED, so concurrent claims never take the same job.
        """
        ...

    async def extend_leases(self, attempts: dict[UUID, int], lease: timedelta) -> None:
        """Push the lease of each running job (id → its attempt) ``lease`` ahead."""
        ...

    async def fail_exhausted(self, max_attempts: int, error: str) -> int:
        """Fail every due job that has used ``max_attempts`` already.

        Such a job is due only because its lease lapsed on its last attempt:
        the worker running it died. Return how many were failed.
        """
        ...

    async def finish(
        self, job_id: UUID, attempt: int, status: JobStatus, error: str | None
    ) -> None:
        """Settle the job as done, discarded or failed."""
        ...

    async def reschedule(
        self, job_id: UUID, attempt: int, delay: timedelta, error: str
    ) -> None:
        """Make the job due again after ``delay``."""
        ...

    async def seconds_until_next_due(self) -> float | None:
        """How long until the next pending job comes due; None when none waits.

        Zero or less means one is due now.
        """
        ...

    async def delete_finished_before(self, days: int) -> int:
        """Delete jobs finished more than ``days`` ago; return the row count."""
        ...
