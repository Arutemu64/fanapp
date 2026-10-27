from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import NotificationORM
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.notification import Notification
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType, generate_notification_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _store(
    dishka_request: AsyncContainer,
    user: User,
    *,
    notification_type: NotificationType,
    mailing_id: MailingId | None,
    minutes_ago: int,
) -> Notification:
    """Store a notification as if it were created ``minutes_ago``.

    The test runs in one wrapping transaction, so the server-side created_at
    would tie across rows; it is set explicitly to order them.
    """
    gateway = await dishka_request.get(NotificationGateway)
    session = await dishka_request.get(AsyncSession)
    notification = Notification(
        id=generate_notification_id(),
        user_id=user.id,
        title="На сцене",
        body="Текст",
        type=notification_type,
        path="/schedule",
        mailing_id=mailing_id,
        seen_at=None,
    )
    await gateway.add_many([notification])
    await session.execute(
        update(NotificationORM)
        .where(NotificationORM.id == notification.id)
        .values(created_at=datetime.now(UTC) - timedelta(minutes=minutes_ago))
    )
    stored = await gateway.get(notification.id, lock=False)
    assert stored is not None
    return stored


async def _mailing(dishka_request: AsyncContainer, user: User) -> MailingId:
    mailing_gateway = await dishka_request.get(MailingGateway)
    mailing = Mailing.create(by_user_id=user.id)
    await mailing_gateway.add(mailing)
    return mailing.id


async def test_older_notification_is_superseded_by_a_later_mailing(
    dishka_request: AsyncContainer, visitor: User, uow: UnitOfWork
) -> None:
    gateway = await dishka_request.get(NotificationGateway)
    first_change = await _mailing(dishka_request, visitor)
    second_change = await _mailing(dishka_request, visitor)
    older = await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_CHANGE,
        mailing_id=first_change,
        minutes_ago=2,
    )
    newer = await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_CHANGE,
        mailing_id=second_change,
        minutes_ago=1,
    )
    await uow.commit()

    assert await gateway.is_superseded(older) is True
    assert await gateway.is_superseded(newer) is False


async def test_parts_of_one_mailing_never_supersede_each_other(
    dishka_request: AsyncContainer, visitor: User, uow: UnitOfWork
) -> None:
    gateway = await dishka_request.get(NotificationGateway)
    change = await _mailing(dishka_request, visitor)
    first_act = await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_SUBSCRIPTION,
        mailing_id=change,
        minutes_ago=2,
    )
    await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_SUBSCRIPTION,
        mailing_id=change,
        minutes_ago=1,
    )
    await uow.commit()

    assert await gateway.is_superseded(first_act) is False


async def test_a_newer_notification_of_another_kind_does_not_supersede(
    dishka_request: AsyncContainer, visitor: User, uow: UnitOfWork
) -> None:
    gateway = await dishka_request.get(NotificationGateway)
    subscription = await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_SUBSCRIPTION,
        mailing_id=await _mailing(dishka_request, visitor),
        minutes_ago=2,
    )
    await _store(
        dishka_request,
        visitor,
        notification_type=NotificationType.SCHEDULE_CHANGE,
        mailing_id=await _mailing(dishka_request, visitor),
        minutes_ago=1,
    )
    await uow.commit()

    assert await gateway.is_superseded(subscription) is False
