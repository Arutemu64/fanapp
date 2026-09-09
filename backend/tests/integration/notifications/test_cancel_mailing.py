from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.cancel_mailing import (
    CancelMailing,
    CancelMailingInput,
)
from fanfan.application.ports.gateways import UserPermissionGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import MailingCancelled
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.notifications import (
    MailingAlreadyCancelled,
    MailingNotCancellable,
    MailingNotFound,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId, MailingStatus
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


async def test_cancel_mailing_marks_cancelled_and_enqueues_event(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await _make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    await interactor(CancelMailingInput(mailing_id=mailing.id))

    stored = await mailing_gateway.read_mailing(mailing.id)
    assert stored is not None
    # Flipped synchronously so ensure_active() rejects in-flight sends at once.
    assert stored.status is MailingStatus.CANCELLED
    # The event drives the consumer that deletes the undelivered notifications.
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(MailingCancelled(mailing_id=mailing.id))


async def test_cancel_mailing_twice_raises_already_cancelled(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await _make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    await interactor(CancelMailingInput(mailing_id=mailing.id))
    with pytest.raises(MailingAlreadyCancelled):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()


async def test_cancel_finished_mailing_raises_not_cancellable(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broadcaster = await _make_broadcaster(dishka_request, uow)
    login(broadcaster)

    mailing = Mailing.create(by_user_id=broadcaster.id)
    await mailing_gateway.add(mailing)
    await mailing_gateway.set_status(
        mailing_id=mailing.id, status=MailingStatus.FINISHED
    )
    await uow.commit()

    with pytest.raises(MailingNotCancellable):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()


async def test_cancel_missing_mailing_raises_not_found(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelMailing)
    broadcaster = await _make_broadcaster(dishka_request, uow)
    login(broadcaster)

    with pytest.raises(MailingNotFound):
        await interactor(CancelMailingInput(mailing_id=MailingId(uuid7())))
    await uow.rollback()


async def test_cancel_mailing_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CancelMailing)
    mailing_gateway = await dishka_request.get(MailingGateway)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    login(visitor)
    with pytest.raises(AccessDenied):
        await interactor(CancelMailingInput(mailing_id=mailing.id))
    await uow.rollback()
