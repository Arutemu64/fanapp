from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import Any, cast
from uuid import uuid7

import pytest
from procrastinate.testing import InMemoryConnector

from fanfan.adapters.procrastinate.job_queue import (
    ProcrastinateJobQueue,
    UnroutedMessageError,
)
from fanfan.application.commands.notifications import CancelMailingCommand
from fanfan.application.interactors.notifications.delete_mailing_notifications import (
    DeleteMailingNotifications,
    DeleteMailingNotificationsInput,
)
from fanfan.core.events.base import Message
from fanfan.core.vo.mailing import MailingId
from fanfan.presentation.worker.app import app, routes
from fanfan.presentation.worker.subscriber import CONTAINER_CONTEXT_KEY

pytestmark = pytest.mark.unit


class _RecordingDeleteMailingNotifications:
    def __init__(self, *, fail_times: int = 0) -> None:
        self.calls: list[MailingId] = []
        self._fail_times = fail_times

    async def __call__(self, data: DeleteMailingNotificationsInput) -> None:
        self.calls.append(data.mailing_id)
        if len(self.calls) <= self._fail_times:
            msg = "transient"
            raise RuntimeError(msg)


class _FakeContainer:
    """Stands in for the worker's Dishka container: one scope, fixed answers."""

    def __init__(self, provides: dict[type, object]) -> None:
        self.provides = provides
        self.scopes_opened = 0

    @asynccontextmanager
    async def __call__(self) -> AsyncIterator[_FakeContainer]:
        self.scopes_opened += 1
        yield self

    async def get(self, dependency_type: type) -> object:
        return self.provides[dependency_type]


@pytest.fixture
def connector() -> Iterator[InMemoryConnector]:
    in_memory = InMemoryConnector()
    with app.replace_connector(in_memory):
        yield in_memory


async def _queue(*messages: Message) -> None:
    # The in-memory connector accepts any object as the caller's connection.
    queue = ProcrastinateJobQueue(app, routes)
    await queue.enqueue(cast("Any", None), messages)


async def _run_worker(container: _FakeContainer) -> None:
    await app.run_worker_async(
        wait=False,
        install_signal_handlers=False,
        additional_context={CONTAINER_CONTEXT_KEY: container},
    )


@pytest.mark.usefixtures("connector")
async def test_queued_command_runs_its_subscriber_in_a_request_scope() -> None:
    interactor = _RecordingDeleteMailingNotifications()
    container = _FakeContainer({DeleteMailingNotifications: interactor})
    mailing_id = MailingId(uuid7())

    await _queue(CancelMailingCommand(mailing_id=mailing_id))
    await _run_worker(container)

    assert interactor.calls == [mailing_id]
    assert container.scopes_opened == 1


async def test_failed_job_is_retried_later(connector: InMemoryConnector) -> None:
    interactor = _RecordingDeleteMailingNotifications(fail_times=1)
    container = _FakeContainer({DeleteMailingNotifications: interactor})

    await _queue(CancelMailingCommand(mailing_id=MailingId(uuid7())))
    await _run_worker(container)

    # Back in the queue for a later run, not settled as failed. (The worker
    # also queued its periodic maintenance jobs; skip those.)
    [job] = [
        job
        for job in connector.jobs.values()
        if job["task_name"] == "notifications:cancel_mailing"
    ]
    assert job["status"] == "todo"
    assert job["attempts"] == 1
    assert job["scheduled_at"] is not None


async def test_job_carries_the_message_and_its_commit_time(
    connector: InMemoryConnector,
) -> None:
    mailing_id = MailingId(uuid7())

    await _queue(CancelMailingCommand(mailing_id=mailing_id))

    [job] = connector.jobs.values()
    assert job["task_name"] == "notifications:cancel_mailing"
    assert job["args"]["message"] == {"mailing_id": str(mailing_id)}
    assert job["args"]["occurred_at"]


@pytest.mark.usefixtures("connector")
async def test_message_without_a_subscriber_is_refused() -> None:
    class Unrouted(Message):
        subject = "test.unrouted"

    with pytest.raises(UnroutedMessageError):
        await _queue(Unrouted())
