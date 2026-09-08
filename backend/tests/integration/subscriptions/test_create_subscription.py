from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionInput,
)
from fanfan.application.ports.gateways.schedule_events import ScheduleEventGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_event import ScheduleEventId, generate_schedule_event_id

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


async def test_create_subscription_persists_for_current_user(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(CreateSubscription)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    login(visitor)

    event = _schedule_event(1, "Событие для подписки", 1)
    await schedule_gateway.add(event)
    await uow.commit()

    result = await interactor(CreateSubscriptionInput(event_id=event.id, counter=5))

    saved = await subscription_gateway.get_by_id(result.subscription_id)
    assert saved is not None
    assert saved.id == result.subscription_id
    assert saved.user_id == visitor.id
    assert saved.event_id == event.id
    assert saved.counter == 5


async def test_create_subscription_for_missing_event_raises_event_not_found(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """Document current behavior: the interactor does not validate the event.

    CreateSubscription injects a ScheduleEventGateway but never uses it, so it
    performs no application-level check that event_id refers to a real event.
    The subscription still cannot be created for a non-existent event because
    the subscriptions.event_id foreign key rejects the INSERT and the gateway
    translates that violation into EventNotFound. So the guard exists only at the
    database layer; lifting it (or an explicit check) into the interactor is a
    candidate for a future plan. If that validation is added, update this test.
    """
    interactor = await dishka_request.get(CreateSubscription)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    login(visitor)

    missing_event_id = ScheduleEventId(UUID("00000000-0000-0000-0000-000000000000"))

    with pytest.raises(EventNotFound):
        await interactor(CreateSubscriptionInput(event_id=missing_event_id, counter=1))

    await uow.rollback()
    assert await subscription_gateway.read_subscriptions_by_user(visitor.id) == []
