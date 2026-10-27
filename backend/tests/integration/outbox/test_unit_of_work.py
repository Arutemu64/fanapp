from typing import ClassVar

import pytest

from fanfan.application.commands.base import Command
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


class _DummyCommand(Command):
    subject: ClassVar[str] = "cmd.tests.dummy"

    value: int


async def _stored(outbox: OutboxGateway) -> list[tuple[str, dict[str, object]]]:
    return [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)]


async def test_enqueued_command_is_stored_on_commit(
    uow: UnitOfWork, outbox: OutboxGateway
) -> None:
    command = _DummyCommand(value=1)

    uow.enqueue(command)
    await uow.commit()

    assert await _stored(outbox) == as_outbox(command)


async def test_rolled_back_command_is_never_stored(
    uow: UnitOfWork, outbox: OutboxGateway
) -> None:
    uow.enqueue(_DummyCommand(value=1))
    await uow.rollback()
    await uow.commit()

    assert await _stored(outbox) == []


async def test_command_is_stored_once_across_commits(
    uow: UnitOfWork, outbox: OutboxGateway
) -> None:
    command = _DummyCommand(value=1)

    uow.enqueue(command)
    await uow.commit()
    await uow.commit()

    assert await _stored(outbox) == as_outbox(command)
