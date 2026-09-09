from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.send_broadcast import (
    SendBroadcast,
    SendBroadcastInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import BroadcastQueued
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _make_broadcaster(dishka_request: AsyncContainer, uow: UnitOfWork) -> User:
    """A user granted notifications:send (no persona fixture exists for it)."""
    user_gateway = await dishka_request.get(UserGateway)
    permission_gateway = await dishka_request.get(UserPermissionGateway)
    broadcaster = User(
        id=UserId(uuid7()),
        username=Username("broadcaster"),
        hashed_password=None,
        role=UserRole.ORG,
    )
    await user_gateway.add(broadcaster)
    await permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.NOTIFICATIONS_SEND,
            user_id=broadcaster.id,
        )
    )
    await uow.commit()
    return broadcaster


async def test_send_broadcast_creates_mailing_and_enqueues_event(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SendBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await _make_broadcaster(dishka_request, uow)
    login(broadcaster)

    roles = [UserRole.VISITOR]
    result = await interactor(SendBroadcastInput(body="Всем привет!", roles=roles))

    mailing = await mailing_gateway.get(result.mailing_id)
    assert mailing is not None
    assert mailing.by_user_id == broadcaster.id
    # The sent text and targeted roles are preserved on the mailing itself, so it
    # outlives the notifications it fans out.
    assert mailing.body == "Всем привет!"
    assert mailing.roles == roles

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        BroadcastQueued(mailing_id=result.mailing_id, body="Всем привет!", roles=roles)
    )


async def test_send_broadcast_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SendBroadcast)
    login(visitor)

    with pytest.raises(AccessDenied):
        await interactor(SendBroadcastInput(body="Нельзя", roles=[UserRole.VISITOR]))

    await uow.rollback()
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []
