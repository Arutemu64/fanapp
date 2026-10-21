import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import ClassVar, cast
from uuid import UUID, uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.jobs import Job
from fanfan.application.interactors.jobs.config import JobsConfig
from fanfan.application.services.job_queue import JobQueue
from fanfan.core.events.base import AppEvent
from fanfan.presentation.worker.router import DiscardJob, JobRouter, RetryJob
from fanfan.presentation.worker.worker import JobWorker

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class _Ping(AppEvent):
    subject: ClassVar[str] = "test.ping"

    outcome: str


class FakeJobQueue(JobQueue):
    """An in-memory queue recording how each job was settled."""

    def __init__(self, jobs: list[Job]) -> None:
        self.pending = list(jobs)
        self.outcomes: dict[UUID, str] = {}
        self.delays: dict[UUID, timedelta] = {}
        self.settled = asyncio.Event()

    async def claim(self, limit: int) -> list[Job]:
        claimed = self.pending[:limit]
        self.pending = self.pending[limit:]
        return [
            job.model_copy(update={"attempts": job.attempts + 1}) for job in claimed
        ]

    async def renew(self, attempts: dict[UUID, int]) -> None:
        pass

    async def seconds_until_next_due(self) -> float | None:
        return None

    async def complete(self, job: Job) -> None:
        self._settle(job, "done")

    async def discard(self, job: Job, reason: str) -> None:  # noqa: ARG002
        self._settle(job, "discarded")

    async def retry_after(self, job: Job, delay: timedelta, reason: str) -> None:  # noqa: ARG002
        self.delays[job.id] = delay
        self._settle(job, "retry_after")

    async def fail_attempt(self, job: Job, error: Exception) -> None:  # noqa: ARG002
        self._settle(job, "failed_attempt")

    async def give_up(
        self,
        job: Job,
        reason: str,  # noqa: ARG002
        error: Exception | None = None,  # noqa: ARG002
    ) -> None:
        self._settle(job, "gave_up")

    def _settle(self, job: Job, outcome: str) -> None:
        self.outcomes[job.id] = outcome
        self.settled.set()


class FakeContainer:
    """Stands in for the Dishka container: every scope resolves the one queue."""

    def __init__(self, queue: FakeJobQueue) -> None:
        self.queue = queue

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[FakeContainer]:
        yield self

    async def get(self, _dependency: type[object]) -> FakeJobQueue:
        return self.queue


class FakeSignal:
    def arm(self) -> None:
        pass

    async def wait(self, timeout: float) -> None:  # noqa: ASYNC109
        await asyncio.sleep(timeout)


router = JobRouter()


@router.handler(_Ping, name="ping")
async def ping(event: _Ping, _job: Job, _container: AsyncContainer) -> None:
    match event.outcome:
        case "retry":
            raise RetryJob(delay=timedelta(seconds=7), reason="later")
        case "discard":
            raise DiscardJob(reason="never")
        case "error":
            msg = "boom"
            raise RuntimeError(msg)


def _job(outcome: str, name: str = "ping") -> Job:
    return Job(
        id=uuid7(),
        name=name,
        payload=_Ping(outcome=outcome).model_dump(mode="json"),
        created_at=datetime.now(UTC),
        trace_headers=None,
        attempts=0,
    )


async def _run_until_settled(jobs: list[Job]) -> FakeJobQueue:
    queue = FakeJobQueue(jobs)
    worker = JobWorker(
        container=cast("AsyncContainer", FakeContainer(queue)),
        router=router,
        signal=FakeSignal(),
        config=JobsConfig(poll_interval_seconds=0.01),
    )
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    try:
        async with asyncio.timeout(2):
            while len(queue.outcomes) < len(jobs):
                queue.settled.clear()
                await queue.settled.wait()
    finally:
        stop.set()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    return queue


async def test_a_handler_that_returns_completes_the_job() -> None:
    job = _job("ok")
    queue = await _run_until_settled([job])
    assert queue.outcomes == {job.id: "done"}


async def test_retry_job_reschedules_with_the_handlers_delay() -> None:
    job = _job("retry")
    queue = await _run_until_settled([job])
    assert queue.outcomes == {job.id: "retry_after"}
    assert queue.delays == {job.id: timedelta(seconds=7)}


async def test_discard_job_drops_the_job() -> None:
    job = _job("discard")
    queue = await _run_until_settled([job])
    assert queue.outcomes == {job.id: "discarded"}


async def test_an_error_counts_a_failed_attempt() -> None:
    job = _job("error")
    queue = await _run_until_settled([job])
    assert queue.outcomes == {job.id: "failed_attempt"}


async def test_a_job_with_no_handler_is_given_up_on() -> None:
    job = _job("ok", name="renamed_away")
    queue = await _run_until_settled([job])
    assert queue.outcomes == {job.id: "gave_up"}


async def test_more_jobs_than_slots_all_run() -> None:
    jobs = [_job("ok") for _ in range(20)]
    queue = await _run_until_settled(jobs)
    assert set(queue.outcomes.values()) == {"done"}
    assert len(queue.outcomes) == 20
