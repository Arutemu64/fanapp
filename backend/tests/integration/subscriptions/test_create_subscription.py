from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionInput,
)
from fanfan.application.ports.gateways.schedule_entries import ScheduleEntryGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_entry import ScheduleBlockStart, ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_entry import (
    ScheduleEntryId,
    generate_schedule_entry_id,
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(number: int, title: str, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=title,
        duration=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
    )


async def test_create_subscription_persists_for_current_user(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(CreateSubscription)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
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
) -> None:
    """An unknown event id is rejected before anything is written.

    CreateSubscription looks the id up with ``get_event``, which finds neither a
    missing id nor a block start. The subscriptions.event_id foreign key, which
    the gateway translates to the same EventNotFound, only backs that check up
    for an event deleted between the lookup and the insert.
    """
    interactor = await dishka_request.get(CreateSubscription)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    login(visitor)

    missing_event_id = ScheduleEntryId(UUID("00000000-0000-0000-0000-000000000000"))

    with pytest.raises(EventNotFound):
        await interactor(CreateSubscriptionInput(event_id=missing_event_id, counter=1))

    await uow.rollback()
    assert await subscription_gateway.read_subscriptions_by_user(visitor.id) == []


async def test_create_subscription_rejects_a_block_start(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    # The FK would accept it, but a block start has no position to remind about.
    interactor = await dishka_request.get(CreateSubscription)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(visitor)

    block = ScheduleBlockStart(
        id=generate_schedule_entry_id(), title="Косплей", order=1
    )
    await schedule_gateway.add(block)
    await uow.commit()

    with pytest.raises(EventNotFound):
        await interactor(CreateSubscriptionInput(event_id=block.id, counter=5))
