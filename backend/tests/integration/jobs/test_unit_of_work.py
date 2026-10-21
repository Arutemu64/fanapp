from datetime import datetime
from uuid import uuid7

import pytest
from dishka import AsyncContainer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.application.commands.notifications import CancelMailingCommand
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.vo.mailing import MailingId
from tests.integration.conftest import JobsReader, as_jobs

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _command() -> CancelMailingCommand:
    return CancelMailingCommand(mailing_id=MailingId(uuid7()))


async def test_enqueued_command_is_queued_on_commit(
    uow: UnitOfWork, jobs: JobsReader
) -> None:
    command = _command()

    uow.enqueue(command)
    await uow.commit()

    assert await jobs() == as_jobs(command)


async def test_rolled_back_command_is_never_queued(
    uow: UnitOfWork, jobs: JobsReader
) -> None:
    uow.enqueue(_command())
    await uow.rollback()
    # A later commit on the same unit of work must not resurrect it.
    await uow.commit()

    assert await jobs() == []


async def test_command_is_queued_once_across_commits(
    uow: UnitOfWork, jobs: JobsReader
) -> None:
    command = _command()

    uow.enqueue(command)
    await uow.commit()
    await uow.commit()

    assert await jobs() == as_jobs(command)


async def test_job_carries_its_commit_time(
    uow: UnitOfWork, dishka_request: AsyncContainer
) -> None:
    uow.enqueue(_command())
    await uow.commit()

    session = await dishka_request.get(AsyncSession)
    args = await session.scalar(text("SELECT args FROM procrastinate_jobs"))
    assert args is not None
    assert datetime.fromisoformat(args["occurred_at"]).tzinfo is not None
    # No span is active in the test, so no trace is stamped on the job.
    assert args["trace_headers"] is None
