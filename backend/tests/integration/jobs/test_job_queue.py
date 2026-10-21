from datetime import timedelta
from uuid import uuid7

import pytest
import sentry_sdk
from dishka import AsyncContainer
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import JobORM
from fanfan.application.dto.jobs import JobStatus
from fanfan.application.interactors.jobs.config import JobsConfig
from fanfan.application.interactors.jobs.purge_jobs import PurgeJobs
from fanfan.application.ports.gateways.jobs import JobGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services.job_queue import JobQueue
from fanfan.core.events.base import AppEvent
from fanfan.core.events.notifications import MailingCancelled, NotificationCreated
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import generate_notification_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def make_queue(
    dishka_request: AsyncContainer, config: JobsConfig | None = None
) -> JobQueue:
    # The test container carries no EnvConfig, so wire the queue by hand with
    # default tuning instead of resolving it from DI.
    return JobQueue(
        job_gateway=await dishka_request.get(JobGateway),
        uow=await dishka_request.get(UnitOfWork),
        config=config or JobsConfig(),
    )


async def enqueue(dishka_request: AsyncContainer, *events: AppEvent) -> None:
    uow = await dishka_request.get(UnitOfWork)
    uow.record_events(events)
    await uow.commit()


def cancelled() -> MailingCancelled:
    return MailingCancelled(mailing_id=MailingId(uuid7()))


async def test_commit_stores_one_job_per_handler(
    dishka_request: AsyncContainer,
) -> None:
    session = await dishka_request.get(AsyncSession)
    event = NotificationCreated(notification_id=generate_notification_id())

    await enqueue(dishka_request, event)

    rows = (await session.scalars(select(JobORM))).all()
    # Each channel send retries on its own, so each is its own job.
    assert {row.name for row in rows} == {
        "send_notification_to_telegram",
        "send_notification_to_vk",
        "send_push_notification",
    }
    assert {row.status for row in rows} == {JobStatus.PENDING}
    assert all(row.payload == event.model_dump(mode="json") for row in rows)


async def test_an_event_no_job_handles_fails_the_commit(
    dishka_request: AsyncContainer,
) -> None:
    class _Unhandled(AppEvent):
        subject = "test.unhandled"

    uow = await dishka_request.get(UnitOfWork)
    uow.record_events([_Unhandled()])

    with pytest.raises(LookupError):
        await uow.commit()


@pytest.mark.usefixtures("tracing")
async def test_jobs_carry_the_trace_of_the_request_that_enqueued_them(
    dishka_request: AsyncContainer,
) -> None:
    # The worker runs a job long after the request that wrote it has ended,
    # from a process with no trace of its own; the job can only join the
    # request's trace if its row carried it.
    session = await dishka_request.get(AsyncSession)
    with sentry_sdk.start_transaction(name="POST /request") as transaction:
        await enqueue(dishka_request, cancelled())

    row = await session.scalar(select(JobORM))
    assert row is not None
    assert row.trace_headers is not None
    assert row.trace_headers["sentry-trace"].startswith(transaction.trace_id)


async def test_claim_takes_due_jobs_in_creation_order_and_leases_them(
    dishka_request: AsyncContainer,
) -> None:
    queue = await make_queue(dishka_request)
    first, second = cancelled(), cancelled()
    # One transaction, so both rows share created_at; the uuid7 id breaks the
    # tie in creation order.
    await enqueue(dishka_request, first, second)

    jobs = await queue.claim(10)

    assert [job.payload for job in jobs] == [
        first.model_dump(mode="json"),
        second.model_dump(mode="json"),
    ]
    assert [job.attempts for job in jobs] == [1, 1]
    # Leased: a second claim must not hand the same jobs out again.
    assert await queue.claim(10) == []


async def test_claim_respects_the_limit(dishka_request: AsyncContainer) -> None:
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled(), cancelled(), cancelled())

    assert len(await queue.claim(2)) == 2
    assert len(await queue.claim(2)) == 1


async def test_a_lapsed_lease_makes_the_job_due_again(
    dishka_request: AsyncContainer,
) -> None:
    # A worker that died stops renewing; once the lease runs out the job is
    # claimed again, as a new attempt.
    queue = await make_queue(dishka_request, JobsConfig(lease_seconds=0))
    await enqueue(dishka_request, cancelled())

    [first] = await queue.claim(1)
    [second] = await queue.claim(1)

    assert second.id == first.id
    assert second.attempts == 2


async def test_completing_a_job_finishes_it(dishka_request: AsyncContainer) -> None:
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    await queue.complete(job)

    row = await session.get(JobORM, job.id)
    assert row is not None
    await session.refresh(row)
    assert row.status is JobStatus.DONE
    assert row.finished_at is not None


async def test_a_stale_attempt_cannot_settle_the_job(
    dishka_request: AsyncContainer,
) -> None:
    # A worker whose lease lapsed finishes late, after another claim took the
    # job; its outcome must not overwrite the newer attempt's.
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request, JobsConfig(lease_seconds=0))
    await enqueue(dishka_request, cancelled())
    [stale] = await queue.claim(1)
    await queue.claim(1)

    await queue.complete(stale)

    row = await session.get(JobORM, stale.id)
    assert row is not None
    await session.refresh(row)
    assert row.status is JobStatus.PENDING


async def test_a_failed_attempt_is_retried_after_a_delay(
    dishka_request: AsyncContainer,
) -> None:
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    await queue.fail_attempt(job, ConnectionError("Telegram is down"))

    row = await session.get(JobORM, job.id)
    assert row is not None
    await session.refresh(row)
    assert row.status is JobStatus.PENDING
    assert row.last_error == "ConnectionError: Telegram is down"
    # Not due yet, so it does not block the claim of the jobs behind it.
    assert await queue.claim(1) == []
    next_due = await queue.seconds_until_next_due()
    assert next_due is not None
    assert 0 < next_due <= 1


async def test_retry_after_waits_out_the_given_delay(
    dishka_request: AsyncContainer,
) -> None:
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    await queue.retry_after(job, timedelta(minutes=10), "flood control")

    next_due = await queue.seconds_until_next_due()
    assert next_due is not None
    assert 590 < next_due <= 600


async def test_the_last_attempt_fails_the_job_for_good(
    dishka_request: AsyncContainer,
) -> None:
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request, JobsConfig(max_attempts=1))
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    await queue.fail_attempt(job, RuntimeError("boom"))

    row = await session.get(JobORM, job.id)
    assert row is not None
    await session.refresh(row)
    assert row.status is JobStatus.FAILED
    assert row.finished_at is not None
    assert await queue.seconds_until_next_due() is None


async def test_discarding_a_job_finishes_it_without_retry(
    dishka_request: AsyncContainer,
) -> None:
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    await queue.discard(job, "User not reachable on VK")

    row = await session.get(JobORM, job.id)
    assert row is not None
    await session.refresh(row)
    assert row.status is JobStatus.DISCARDED
    assert row.last_error == "User not reachable on VK"


async def test_renew_pushes_the_lease_of_running_jobs(
    dishka_request: AsyncContainer,
) -> None:
    queue = await make_queue(dishka_request, JobsConfig(lease_seconds=0))
    await enqueue(dishka_request, cancelled())
    [job] = await queue.claim(1)

    long_lease = await make_queue(dishka_request, JobsConfig(lease_seconds=60))
    await long_lease.renew({job.id: job.attempts})

    assert await queue.claim(1) == []


async def test_purge_drops_only_old_finished_jobs(
    dishka_request: AsyncContainer,
) -> None:
    session = await dishka_request.get(AsyncSession)
    queue = await make_queue(dishka_request)
    await enqueue(dishka_request, cancelled(), cancelled())
    old, pending = await queue.claim(2)
    await queue.complete(old)
    await session.execute(
        update(JobORM)
        .where(JobORM.id == old.id)
        .values(finished_at=JobORM.finished_at - timedelta(days=8))
    )

    purge = PurgeJobs(
        job_gateway=await dishka_request.get(JobGateway),
        uow=await dishka_request.get(UnitOfWork),
        config=JobsConfig(retention_days=7),
    )
    await purge()

    remaining = (await session.scalars(select(JobORM.id))).all()
    assert remaining == [pending.id]
