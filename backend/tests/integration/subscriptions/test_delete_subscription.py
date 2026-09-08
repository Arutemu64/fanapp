from collections.abc import Callable
from uuid import UUID, uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.subscriptions.delete_subscription import (
    DeleteSubscription,
    DeleteSubscriptionInput,
)
from fanfan.application.ports.gateways.schedule_events import ScheduleEventGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.subscriptions import SubscriptionNotFound
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.subscription import Subscription
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_event import generate_schedule_event_id
from fanfan.core.vo.subscription import (
    SubscriptionId,
    generate_subscription_id,
)
from fanfan.core.vo.user import UserId, Username, UserRole

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(number: int, title: str, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=title,
        duration=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_delete_subscription_removes_own_subscription(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(DeleteSubscription)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    login(visitor)

    event = _schedule_event(1, "Событие", 1)
    await schedule_gateway.add(event)
    # Commit the event first: the subscription's FK to schedule_events must see a
    # persisted row, and the gateway's flush([...]) only flushes the subscription.
    await uow.commit()
    subscription = Subscription(
        id=generate_subscription_id(),
        user_id=visitor.id,
        event_id=event.id,
        counter=3,
    )
    await subscription_gateway.add(subscription)
    await uow.commit()

    await interactor(DeleteSubscriptionInput(subscription_id=subscription.id))

    assert await subscription_gateway.get_by_id(subscription.id) is None


async def test_delete_subscription_missing_raises_not_found(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
):
    interactor = await dishka_request.get(DeleteSubscription)
    login(visitor)

    missing_id = SubscriptionId(UUID("00000000-0000-0000-0000-000000000000"))

    with pytest.raises(SubscriptionNotFound):
        await interactor(DeleteSubscriptionInput(subscription_id=missing_id))


async def test_delete_subscription_of_another_user_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """IDOR guard: a user must not delete a subscription they do not own.

    User A owns the subscription; user B tries to delete it by id and is
    rejected with AccessDenied, and the subscription is left intact.
    """
    interactor = await dishka_request.get(DeleteSubscription)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    user_gateway = await dishka_request.get(UserGateway)

    # visitor (user A) owns the subscription; other_user (user B) attacks it.
    other_user = User(
        id=UserId(uuid7()),
        username=Username("other_visitor"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(other_user)
    event = _schedule_event(1, "Событие", 1)
    await schedule_gateway.add(event)
    # Commit the event first so the subscription's FK sees a persisted row.
    await uow.commit()
    subscription = Subscription(
        id=generate_subscription_id(),
        user_id=visitor.id,
        event_id=event.id,
        counter=3,
    )
    await subscription_gateway.add(subscription)
    await uow.commit()

    login(other_user)
    with pytest.raises(AccessDenied):
        await interactor(DeleteSubscriptionInput(subscription_id=subscription.id))

    still_there = await subscription_gateway.get_by_id(subscription.id)
    assert still_there is not None
    assert still_there.user_id == visitor.id
