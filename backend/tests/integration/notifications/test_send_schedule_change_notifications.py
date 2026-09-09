from collections.abc import Callable
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.gateways.schedule_events import ScheduleEventGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.notifications import NotificationQueued
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.subscription import Subscription
from fanfan.core.models.user import User
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.schedule_event import generate_schedule_event_id
from fanfan.core.vo.subscription import generate_subscription_id
from fanfan.core.vo.user import UserId, Username, UserRole
from tests.fakes.event_broker import FakeEventBroker

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(
    number: int, title: str, order: float, *, is_current: bool = False
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=title,
        duration=15,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_schedule_change_notifies_only_subscribers_in_window(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """Subscription fan-out honours the window and carries the queue difference.

    Layout by (order, queue): current=(1,1), B=(2,2), C=(3,3). A MOVED change
    targets C. The window condition is
    current.order <= changed.order <= subscription.event.order, so:
      * a subscriber to C (order 3) is inside the window and is notified, with
        queue_difference = C.queue - current.queue = 3 - 1 = 2;
      * a subscriber to B (order 2) is outside it (3 > 2) and is not notified.
    The change carries no user and next_event_changed=False, so neither the
    editor nor the global-announcement branch fires — only subscriptions do.
    """
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    user_gateway = await dishka_request.get(UserGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    current_event = _schedule_event(1, "Текущее", 1, is_current=True)
    event_b = _schedule_event(2, "Событие B", 2)
    event_c = _schedule_event(3, "Событие C", 3)
    await schedule_gateway.add(current_event)
    await schedule_gateway.add(event_b)
    await schedule_gateway.add(event_c)
    # Commit the events first so the subscriptions' FK sees persisted rows; the
    # gateway's flush([...]) only flushes the subscription being added.
    await uow.commit()

    # visitor subscribes to C (inside the window); a second user to B (outside).
    subscriber_outside = User(
        id=UserId(uuid7()),
        username=Username("subscriber_b"),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(subscriber_outside)
    await subscription_gateway.add(
        Subscription(
            id=generate_subscription_id(),
            user_id=visitor.id,
            event_id=event_c.id,
            counter=5,
        )
    )
    await subscription_gateway.add(
        Subscription(
            id=generate_subscription_id(),
            user_id=subscriber_outside.id,
            event_id=event_b.id,
            counter=5,
        )
    )

    change = ScheduleChange.moved(
        event_id=event_c.id,
        previous_event_id=None,
        mailing_id=None,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(SendScheduleChangeNotificationsInput(schedule_change_id=change.id))

    published = [
        e for e in broker.published_events if isinstance(e, NotificationQueued)
    ]
    assert len(published) == 1
    event = published[0]
    assert event.notification.user_id == visitor.id
    assert event.notification.type is NotificationType.SCHEDULE_SUBSCRIPTION
    # queue_difference = 3 - 1 = 2 is rendered into the body.
    assert "2 выступления" in event.notification.body
    assert "Событие C" in event.notification.body


async def test_schedule_change_fan_out_reuses_ids_across_redelivery(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    """A redelivered schedule-change trigger mints the same notification ids.

    The trigger is delivered at-least-once, so the interactor can run twice for
    one change. The notifications insert dedups on id (on-conflict-do-nothing),
    so a rerun that produced fresh random ids would duplicate every recipient's
    notification. Running the interactor twice must yield the same id for the
    same recipient.
    """
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    broker = await dishka_request.get(FakeEventBroker)
    login(visitor)

    current_event = _schedule_event(1, "Текущее", 1, is_current=True)
    event_c = _schedule_event(3, "Событие C", 3)
    await schedule_gateway.add(current_event)
    await schedule_gateway.add(event_c)
    await uow.commit()

    await subscription_gateway.add(
        Subscription(
            id=generate_subscription_id(),
            user_id=visitor.id,
            event_id=event_c.id,
            counter=5,
        )
    )
    change = ScheduleChange.moved(
        event_id=event_c.id,
        previous_event_id=None,
        mailing_id=None,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    data = SendScheduleChangeNotificationsInput(schedule_change_id=change.id)
    await interactor(data)
    await interactor(data)

    published = [
        e for e in broker.published_events if isinstance(e, NotificationQueued)
    ]
    # Both runs target the one in-window subscriber; the id is identical, so the
    # gateway upsert would no-op the second insert instead of duplicating it.
    assert len(published) == 2
    assert published[0].notification.id == published[1].notification.id
