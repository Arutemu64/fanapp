from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.commands.notifications import ProcessBroadcastCommand
from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcast,
    SendBroadcastInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.notifications import MailingAlreadyExists
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.user import UserRole
from tests.integration.conftest import JobsReader, as_jobs, make_broadcaster


def _broadcast(body: str, roles: list[UserRole]) -> SendBroadcastInput:
    return SendBroadcastInput(mailing_id=MailingId(uuid7()), body=body, roles=roles)


pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_send_broadcast_creates_mailing_and_enqueues_event(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    jobs: JobsReader,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SendBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)

    roles = [UserRole.VISITOR]
    result = await interactor(_broadcast("Всем привет!", roles))

    mailing = await mailing_gateway.get(result.mailing_id)
    assert mailing is not None
    assert mailing.by_user_id == broadcaster.id
    # The sent text and targeted roles are preserved on the mailing itself, so it
    # outlives the notifications it fans out.
    assert mailing.body == "Всем привет!"
    assert mailing.roles == roles

    assert await jobs() == as_jobs(
        ProcessBroadcastCommand(
            mailing_id=result.mailing_id, body="Всем привет!", roles=roles
        )
    )


async def test_send_broadcast_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    jobs: JobsReader,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SendBroadcast)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(_broadcast("Нельзя", [UserRole.VISITOR]))

    await uow.rollback()
    assert await jobs() == []


async def test_send_broadcast_replay_returns_the_mailing_without_resending(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    jobs: JobsReader,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SendBroadcast)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)
    data = _broadcast("Всем привет!", [UserRole.VISITOR])

    first = await interactor(data)
    # The response to the first call was lost; the client sends it again.
    second = await interactor(data)

    assert second.mailing_id == first.mailing_id == data.mailing_id
    assert await jobs() == as_jobs(
        ProcessBroadcastCommand(
            mailing_id=first.mailing_id, body="Всем привет!", roles=[UserRole.VISITOR]
        )
    )


async def test_send_broadcast_with_a_taken_id_raises_already_exists(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SendBroadcast)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)
    data = _broadcast("Всем привет!", [UserRole.VISITOR])
    await interactor(data)

    with pytest.raises(MailingAlreadyExists):
        await interactor(data.model_copy(update={"body": "Другой текст"}))


async def test_overlapping_send_loses_the_insert_race_with_already_exists(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    jobs: JobsReader,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(SendBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await make_broadcaster(dishka_request, uow)
    login(broadcaster)
    data = _broadcast("Всем привет!", [UserRole.VISITOR])
    first = await interactor(data)

    # The overlapping request missed the interactor's lookup before the first
    # committed, so its INSERT is what meets the taken ID.
    racer = Mailing.create(by_user_id=broadcaster.id, mailing_id=data.mailing_id)
    racer.queue_broadcast(body=data.body, roles=data.roles)
    with pytest.raises(MailingAlreadyExists):
        await mailing_gateway.add(racer)

    await uow.rollback()
    assert await jobs() == as_jobs(
        ProcessBroadcastCommand(
            mailing_id=first.mailing_id, body="Всем привет!", roles=[UserRole.VISITOR]
        )
    )
