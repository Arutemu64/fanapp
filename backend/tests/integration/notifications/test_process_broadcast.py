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
from fanfan.core.exceptions.notifications import MailingNotFound
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.user import User
from fanfan.core.vo.mailing import MailingId, MailingStatus
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.fakes.event_broker import FakeEventBroker
from tests.integration.notifications.delivered import delivered_notifications

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
) -> None:
    """Characterization baseline for the broadcast fan-out (Plan 007 builds here).

    ProcessBroadcast reads every user matching the roles, records that count as
    the mailing total, and stores and hands over exactly one notification per
    user. The recipient set is compared against read_ids_by_roles so
    the assertion holds regardless of any seeded users of that role.
    """
    interactor = await dishka_request.get(ProcessBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    user_gateway = await dishka_request.get(UserGateway)
    login(visitor)

    created = await _add_users(dishka_request, uow, count=3, role=UserRole.VOLUNTEER)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    body = "Рассылка для волонтёров"
    await interactor(
        ProcessBroadcastInput(
            mailing_id=mailing.id, body=body, roles=[UserRole.VOLUNTEER]
        )
    )

    expected_ids = set(await user_gateway.read_ids_by_roles(UserRole.VOLUNTEER))
    assert {u.id for u in created} <= expected_ids

    delivered = await delivered_notifications(dishka_request)
    recipient_ids = [n.user_id for n in delivered]
    # One notification per matching user, each targeting a distinct recipient.
    assert len(delivered) == len(expected_ids)
    assert set(recipient_ids) == expected_ids
    assert len(recipient_ids) == len(set(recipient_ids))

    for notification in delivered:
        assert notification.type is NotificationType.BROADCAST
        assert notification.body == body
        assert notification.mailing_id == mailing.id

    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    # Every notification is stored by the time the fan-out returns, so the
    # mailing is already FINISHED.
    assert stored.total_count == len(expected_ids)
    assert stored.status is MailingStatus.FINISHED


async def test_process_broadcast_with_no_recipients_finishes_immediately(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
) -> None:
    """A broadcast that reaches nobody is done at once, not stuck PENDING forever.

    With no matching users no chunk is stored to finish it, so the fan-out
    finishes it on its own.
    """
    interactor = await dishka_request.get(ProcessBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    # No PARTICIPANT users exist in the isolated test transaction.
    await interactor(
        ProcessBroadcastInput(
            mailing_id=mailing.id, body="Никому", roles=[UserRole.PARTICIPANT]
        )
    )

    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    assert stored.total_count == 0
    assert stored.status is MailingStatus.FINISHED
    assert broker.published_events == []


async def test_process_broadcast_missing_mailing_raises_not_found(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(ProcessBroadcast)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    await _add_users(dishka_request, uow, count=1, role=UserRole.VOLUNTEER)

    with pytest.raises(MailingNotFound):
        await interactor(
            ProcessBroadcastInput(
                mailing_id=MailingId(uuid7()),
                body="Нет рассылки",
                roles=[UserRole.VOLUNTEER],
            )
        )

    assert broker.published_events == []


async def test_process_broadcast_rerun_yields_identical_notification_ids(
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
) -> None:
    """A redelivered broadcast trigger reuses the same notification ids.

    ProcessBroadcast derives each notification's id from (mailing_id, user_id),
    so rerunning it for the same mailing (as a redelivery of the broadcast
    message would) produces the exact same set of ids rather than duplicates,
    and finishes the mailing with the same recipient count.
    """
    interactor = await dishka_request.get(ProcessBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    await _add_users(dishka_request, uow, count=3, role=UserRole.VOLUNTEER)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    await uow.commit()

    run_input = ProcessBroadcastInput(
        mailing_id=mailing.id, body="Повторная рассылка", roles=[UserRole.VOLUNTEER]
    )
    await interactor(run_input)
    first_ids = {n.id for n in await delivered_notifications(dishka_request)}

    broker.published_events.clear()
    await interactor(run_input)
    second_ids = {n.id for n in await delivered_notifications(dishka_request)}

    assert first_ids
    assert first_ids == second_ids
    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    assert stored.total_count == len(first_ids)
    assert stored.status is MailingStatus.FINISHED


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (MailingStatus.PENDING, MailingStatus.FAILED),
        (MailingStatus.FINISHED, MailingStatus.FINISHED),
    ],
)
async def test_process_broadcast_abandon_fails_an_unfinished_mailing(
    *,
    dishka_request: AsyncContainer,
    login: Callable[[User], None],
    visitor: User,
    uow: UnitOfWork,
    status: MailingStatus,
    expected: MailingStatus,
) -> None:
    """Out of redeliveries, the handler abandons the broadcast so it does not
    stay PENDING forever; a finished one is already settled."""
    interactor = await dishka_request.get(ProcessBroadcast)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(visitor)

    mailing = Mailing.create(by_user_id=visitor.id)
    mailing.status = status
    await mailing_gateway.add(mailing)
    await uow.commit()

    await interactor.abandon(mailing.id)

    stored = await mailing_gateway.get(mailing.id, lock=False)
    assert stored is not None
    assert stored.status is expected
