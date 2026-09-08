from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.process_broadcast import (
    ProcessBroadcast,
    ProcessBroadcastInput,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.fakes.event_broker import FakeEventBroker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def _add_users(
    dishka_request: AsyncContainer, uow: UnitOfWork, count: int, role: UserRole
) -> list[User]:
    user_gateway = await dishka_request.get(UserGateway)
    users = [
        User(
            id=UserId(uuid7()),
            username=Username(f"{role.value}_{i}"),
            hashed_password=None,
            role=role,
        )
        for i in range(count)
    ]
    for user in users:
        await user_gateway.add(user)
    await uow.commit()
    return users


async def test_process_broadcast_sets_total_and_fans_out_one_per_user(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
):
    """Characterization baseline for the broadcast fan-out (Plan 007 builds here).

    ProcessBroadcast reads every user matching the roles, records that count as
    the mailing total, and publishes exactly one NotificationQueued per user via
    the EventBroker. The recipient set is compared against read_all_by_roles so
    the assertion holds regardless of any seeded users of that role.
    """
    interactor = await dishka_request.get(ProcessBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    user_gateway = await dishka_request.get(UserGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    created = await _add_users(dishka_request, uow, count=3, role=UserRole.HELPER)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    body = "Рассылка для волонтёров"
    await interactor(
        ProcessBroadcastInput(mailing_id=mailing.id, body=body, roles=[UserRole.HELPER])
    )

    expected_ids = {u.id for u in await user_gateway.read_all_by_roles(UserRole.HELPER)}
    assert {u.id for u in created} <= expected_ids

    published = [
        e for e in broker.published_events if isinstance(e, NotificationQueued)
    ]
    recipient_ids = [e.notification.user_id for e in published]
    # One event per matching user, each targeting a distinct recipient.
    assert len(published) == len(expected_ids)
    assert set(recipient_ids) == expected_ids
    assert len(recipient_ids) == len(set(recipient_ids))

    for event in published:
        assert event.notification.type is NotificationType.BROADCAST
        assert event.notification.body == body
        assert event.notification.mailing_id == mailing.id

    stored = await mailing_gateway.read_mailing(mailing.id)
    assert stored is not None
    assert stored.total_count == len(expected_ids)


async def test_process_broadcast_missing_mailing_raises_not_found(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ProcessBroadcast)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    await _add_users(dishka_request, uow, count=1, role=UserRole.HELPER)

    with pytest.raises(MailingNotFound):
        await interactor(
            ProcessBroadcastInput(
                mailing_id=MailingId(uuid7()),
                body="Нет рассылки",
                roles=[UserRole.HELPER],
            )
        )

    assert [
        e for e in broker.published_events if isinstance(e, NotificationQueued)
    ] == []
