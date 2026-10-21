import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

import sentry_sdk
from dishka import AsyncContainer
from sentry_sdk.tracing import TransactionSource

from fanfan.application.dto.jobs import Job
from fanfan.application.interactors.jobs.config import JobsConfig
from fanfan.application.ports.job_signal import JobSignal
from fanfan.application.services.job_queue import JobQueue
from fanfan.presentation.worker.router import DiscardJob, JobRouter, RetryJob

logger = logging.getLogger(__name__)

# Sentry's queue instrumentation contract: this span op and the data keys below
# are what its Queues view reads.
# https://docs.sentry.io/platforms/python/tracing/instrumentation/custom-instrumentation/queues-module/
_PROCESS_OP = "queue.process"

# Floor for the idle wait. A claim can come back empty while a job is already
# due, when another worker holds its row for a moment; without a floor the loop
# would spin on that until the row is released.
_MIN_WAIT_SECONDS = 0.1

# How long a shutdown waits for running jobs before cancelling them. Inside
# Docker's 10 s stop grace period, with room for the container to close. A
# cancelled job is not settled: its lease lapses and it runs again.
_SHUTDOWN_GRACE_SECONDS = 5.0


@dataclass(slots=True)
class _Running:
    task: asyncio.Task[None]
    # The attempt this worker now holds the job under. A job whose lease lapsed
    # while it ran can be claimed again by this same worker; that claim counts a
    # new attempt, and settling under the old one would be ignored.
    attempt: int


class JobWorker:
    """Claim due jobs and run them, up to ``concurrency`` at a time.

    Claims on every NOTIFY, when a retry falls due, and at least once per poll
    interval. While a job runs its lease is renewed on a heartbeat, so a long
    sync is never handed to a second worker; if this worker dies, the leases
    lapse and the jobs run again elsewhere. At-least-once: a job is settled only
    after its handler returns, so handlers must be idempotent.
    """

    def __init__(
        self,
        container: AsyncContainer,
        router: JobRouter,
        signal: JobSignal,
        config: JobsConfig,
    ) -> None:
        self._container = container
        self._router = router
        self._signal = signal
        self._config = config
        self._running: dict[UUID, _Running] = {}

    async def run(self, stop: asyncio.Event) -> None:
        heartbeat = asyncio.create_task(self._heartbeat(), name="jobs-heartbeat")
        try:
            while not stop.is_set():
                self._signal.arm()
                free = self._config.concurrency - len(self._running)
                if free > 0 and await self._claim(free) == free:
                    # A full claim may have left more due jobs behind; claim
                    # again as soon as a slot frees up.
                    continue
                await self._wait(stop, free)
        finally:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
            await self._shutdown()

    async def _claim(self, limit: int) -> int:
        try:
            async with self._container() as scope:
                queue = await scope.get(JobQueue)
                jobs = await queue.claim(limit)
        except Exception:
            # The database is down or the claim broke; the next wake retries.
            logger.exception("Job claim failed", extra={"job_event": "claim_failed"})
            sentry_sdk.capture_exception()
            return 0
        for job in jobs:
            running = self._running.get(job.id)
            if running is not None:
                running.attempt = job.attempts
                continue
            task = asyncio.create_task(self._run_job(job), name=f"job-{job.name}")
            self._running[job.id] = _Running(task=task, attempt=job.attempts)
            task.add_done_callback(lambda _task, job_id=job.id: self._forget(job_id))
        return len(jobs)

    def _forget(self, job_id: UUID) -> None:
        self._running.pop(job_id, None)

    async def _wait(self, stop: asyncio.Event, free: int) -> None:
        wakers: list[asyncio.Future[object]] = [asyncio.ensure_future(stop.wait())]
        running_tasks: list[asyncio.Task[None]] = []
        if free > 0:
            timeout = await self._idle_timeout()
            wakers.append(asyncio.ensure_future(self._signal.wait(timeout)))
        else:
            # Every slot is taken: only a finishing job makes room to claim.
            running_tasks = [running.task for running in self._running.values()]
            poll = asyncio.sleep(self._config.poll_interval_seconds)
            wakers.append(asyncio.ensure_future(poll))
        await asyncio.wait(
            [*wakers, *running_tasks], return_when=asyncio.FIRST_COMPLETED
        )
        # Only the wakers are ours to cancel; the jobs keep running.
        for waker in wakers:
            waker.cancel()

    async def _idle_timeout(self) -> float:
        timeout = self._config.poll_interval_seconds
        try:
            async with self._container() as scope:
                queue = await scope.get(JobQueue)
                next_due = await queue.seconds_until_next_due()
        except Exception:
            logger.warning("Could not read the next job's due time", exc_info=True)
            return timeout
        if next_due is not None:
            timeout = min(timeout, next_due)
        return max(timeout, _MIN_WAIT_SECONDS)

    async def _heartbeat(self) -> None:
        # A third of the lease, so a beat can be missed before it lapses.
        interval = self._config.lease_seconds / 3
        while True:
            await asyncio.sleep(interval)
            attempts = {
                job_id: running.attempt for job_id, running in self._running.items()
            }
            try:
                async with self._container() as scope:
                    queue = await scope.get(JobQueue)
                    await queue.renew(attempts)
            except Exception:
                # A missed beat only risks a job running twice once its lease
                # lapses; keep beating.
                logger.warning("Could not renew job leases", exc_info=True)

    async def _run_job(self, job: Job) -> None:
        # One isolation scope per job: jobs run side by side in one process,
        # and tags or breadcrumbs from one must not leak into another.
        with sentry_sdk.isolation_scope():
            transaction = sentry_sdk.continue_trace(
                job.trace_headers or {},
                op=_PROCESS_OP,
                name=job.name,
                source=TransactionSource.TASK,
            )
            with (
                sentry_sdk.start_transaction(transaction),
                sentry_sdk.start_span(op=_PROCESS_OP, name=job.name) as span,
            ):
                span.set_data("messaging.message.id", str(job.id))
                span.set_data("messaging.destination.name", job.name)
                span.set_data("messaging.message.retry.count", job.attempts - 1)
                # Time the job waited since it was enqueued, in ms.
                waited = datetime.now(UTC) - job.created_at
                span.set_data(
                    "messaging.message.receive.latency", waited.total_seconds() * 1000
                )
                await self._run_and_settle(job)

    async def _run_and_settle(self, job: Job) -> None:
        handler = self._router.get(job.name)
        retry: RetryJob | None = None
        discard_reason: str | None = None
        error: Exception | None = None
        started = time.monotonic()
        if handler is None:
            # Unknown names come from a handler renamed or removed while its
            # jobs were pending; retrying would not bring the handler back.
            error = LookupError(f"No handler named {job.name!r}")
        else:
            try:
                async with self._container() as scope:
                    await handler(job, scope)
            except RetryJob as e:
                retry = e
            except DiscardJob as e:
                discard_reason = e.reason
            # Blind on purpose: whatever the handler raises, the job must be
            # retried rather than left to wait out its lease.
            except Exception as e:  # noqa: BLE001
                # Reported here, inside the job's transaction, so the error
                # links to the trace that enqueued the job.
                sentry_sdk.capture_exception(e)
                error = e

        job = self._as_current_attempt(job)
        try:
            async with self._container() as scope:
                queue = await scope.get(JobQueue)
                if handler is None and error is not None:
                    outcome = "gave_up"
                    await queue.give_up(job, str(error), error)
                elif retry is not None:
                    outcome = "retry_after"
                    await queue.retry_after(job, retry.delay, retry.reason)
                elif discard_reason is not None:
                    outcome = "discarded"
                    await queue.discard(job, discard_reason)
                elif error is not None:
                    outcome = "failed_attempt"
                    await queue.fail_attempt(job, error)
                else:
                    outcome = "done"
                    await queue.complete(job)
        except Exception:
            # The outcome is lost, not the job: its lease lapses and it runs
            # again, which an idempotent handler absorbs.
            logger.exception(
                "Could not settle a job",
                extra={"job_id": str(job.id), "job_name": job.name},
            )
            sentry_sdk.capture_exception()
            return
        logger.info(
            "Job ran",
            extra={
                "job_id": str(job.id),
                "job_name": job.name,
                "attempt": job.attempts,
                "outcome": outcome,
                "duration_ms": round((time.monotonic() - started) * 1000),
            },
        )

    def _as_current_attempt(self, job: Job) -> Job:
        # Still tracked while it settles, so shutdown waits for the write.
        running = self._running.get(job.id)
        if running is None or running.attempt == job.attempts:
            return job
        return job.model_copy(update={"attempts": running.attempt})

    async def _shutdown(self) -> None:
        tasks = [running.task for running in self._running.values()]
        if not tasks:
            return
        logger.info("Waiting for running jobs", extra={"job_count": len(tasks)})
        _, unfinished = await asyncio.wait(tasks, timeout=_SHUTDOWN_GRACE_SECONDS)
        for task in unfinished:
            task.cancel()
        if unfinished:
            await asyncio.gather(*unfinished, return_exceptions=True)
            logger.warning(
                "Cancelled jobs still running at shutdown; they will run again",
                extra={"job_count": len(unfinished)},
            )
