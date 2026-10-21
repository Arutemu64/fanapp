from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.application.services import notification_fan_out
from fanfan.application.services.notification_fan_out import NotificationFanOut
from fanfan.core.exceptions.notifications import MailingAlreadyCancelled
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.notification import NewNotification
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.notification import NotificationType, notification_id_for
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.fakes.event_broker import FakeEventBroker
from tests.fakes.realtime_gateway import FakeRealtimeGateway
from tests.integration.notifications.delivered import delivered_notifications

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _recipients(
    dishka_request: AsyncContainer, uow: UnitOfWork, count: int
) -> list[User]:
    user_gateway = await dishka_request.get(UserGateway)
    users = [
        User(
            id=UserId(uuid7()),
            username=Username(f"recipient_{i}"),
            hashed_password=None,
            role=UserRole.VISITOR,
        )
        for i in range(count)
    ]
    for user in users:
        await user_gateway.add(user)
    await uow.commit()
    return users


def _broadcast(mailing: Mailing, users: list[User]) -> list[NewNotification]:
    return [
        NewNotification(
            id=notification_id_for(mailing.id, user.id),
            user_id=user.id,
            title="Рассылка от организаторов",
            body="Текст <script>alert(1)</script>рассылки",
            path="/notifications",
            mailing_id=mailing.id,
            type=NotificationType.BROADCAST,
        )
        for user in users
    ]


async def test_fan_out_stores_every_chunk_and_finishes_the_mailing(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Three recipients in chunks of two: the second chunk finishes it."""
    monkeypatch.setattr(notification_fan_out, "_CHUNK_SIZE", 2)
    fan_out = await dishka_request.get(NotificationFanOut)
    mailing_gateway = await dishka_request.get(MailingGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(visitor)

    users = await _recipients(dishka_request, uow, count=3)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    await fan_out(_broadcast(mailing, users), mailing_id=mailing.id)

    delivered = await delivered_notifications(dishka_request)
    assert {n.user_id for n in delivered} == {u.id for u in users}
    # Sanitized once, on the way in, for every channel.
    assert all("<script>" not in n.body for n in delivered)
    # Every recipient gets the live toast.
    assert {user_id for user_id, _ in realtime.published} == {u.id for u in users}
    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    assert stored.total_count == 3
    assert stored.status is MailingStatus.FINISHED


async def test_fan_out_of_a_cancelled_mailing_stores_nothing(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
) -> None:
    fan_out = await dishka_request.get(NotificationFanOut)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    users = await _recipients(dishka_request, uow, count=2)
    mailing = Mailing.create(by_user_id=visitor.id)
    mailing.cancel()
    await mailing_gateway.add(mailing)
    await uow.commit()

    with pytest.raises(MailingAlreadyCancelled):
        await fan_out(_broadcast(mailing, users), mailing_id=mailing.id)

    assert broker.published_events == []
    assert await delivered_notifications(dishka_request) == []
    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    assert stored.status is MailingStatus.CANCELLED


async def test_fan_out_refuses_notifications_of_several_mailings(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
) -> None:
    # One mailing per call is what lets a chunk lock a single mailing row.
    fan_out = await dishka_request.get(NotificationFanOut)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(visitor)

    users = await _recipients(dishka_request, uow, count=1)
    first = Mailing.create(by_user_id=visitor.id)
    second = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(first)
    await mailing_gateway.add(second)
    await uow.commit()

    with pytest.raises(ValueError, match="one mailing"):
        await fan_out([*_broadcast(first, users), *_broadcast(second, users)])
