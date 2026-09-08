from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.create_notification import (
    CreateNotification,
    CreateNotificationInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.notifications import NotificationGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.notification import NewNotification, Notification
from fanfan.core.models.user import User
from fanfan.core.vo.notification import (
    NotificationType,
    generate_notification_id,
    notification_id_for,
)
from fanfan.core.vo.user import UserId

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _broadcast_notification(mailing: Mailing, user: User) -> NewNotification:
    return NewNotification(
        id=notification_id_for(mailing.id, user.id),
        user_id=user.id,
        title="Рассылка от организаторов",
        body="Текст рассылки",
        path="/notifications",
        mailing_id=mailing.id,
        type=NotificationType.BROADCAST,
    )


async def test_create_notification_redelivery_is_a_single_row_single_increment(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
):
    """Plan 007: a redelivered NotificationQueued must not double-count or duplicate.

    Calling CreateNotification twice with the same (mailing-derived) id — as a
    redelivery of the same NATS message would — must insert exactly one row and
    increment the mailing's sent_count exactly once, instead of raising an
    IntegrityError (which would nack-and-redeliver forever) or drifting the count.
    """
    interactor = await dishka_request.get(CreateNotification)
    mailing_gateway = await dishka_request.get(MailingGateway)
    notification_gateway = await dishka_request.get(NotificationGateway)
    login(visitor)

    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await mailing_gateway.set_total(mailing_id=mailing.id, total_count=1)
    await uow.commit()

    notification = _broadcast_notification(mailing, visitor)
    data = CreateNotificationInput(notification=notification)

    first_id = await interactor(data)
    second_id = await interactor(data)

    assert first_id == second_id == notification.id

    stored = await notification_gateway.get(notification.id)
    assert stored is not None
    assert stored.body == notification.body

    stored_mailing = await mailing_gateway.read_mailing(mailing.id)
    assert stored_mailing is not None
    assert stored_mailing.sent_count == 1


async def test_create_notification_gateway_add_reports_whether_it_inserted(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
):
    """The gateway upsert is the primitive CreateNotification relies on."""
    notification_gateway = await dishka_request.get(NotificationGateway)
    login(visitor)

    notification = Notification(
        id=generate_notification_id(),
        user_id=UserId(visitor.id),
        title="Заголовок",
        body="Тело",
        type=NotificationType.DEFAULT,
        path=None,
        mailing_id=None,
        seen_at=None,
    )

    inserted_first = await notification_gateway.add(notification)
    await uow.commit()
    inserted_second = await notification_gateway.add(notification)
    await uow.commit()

    assert inserted_first is True
    assert inserted_second is False
