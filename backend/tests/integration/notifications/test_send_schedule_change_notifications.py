from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid7

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.notifications.send_schedule_change_notifications import (  # noqa: E501
    SendScheduleChangeNotifications,
    SendScheduleChangeNotificationsInput,
)
from fanfan.application.ports.gateways import ScheduleChangeGateway
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.schedule_entries import ScheduleEntryGateway
from fanfan.application.ports.gateways.subscriptions import SubscriptionGateway
from fanfan.application.ports.gateways.user_permissions import UserPermissionGateway
from fanfan.application.ports.gateways.users import UserGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.permission import UserPermission
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.subscription import Subscription
from fanfan.core.models.user import User, UserSettings
from fanfan.core.vo.mailing import MailingStatus
from fanfan.core.vo.notification import NotificationType
from fanfan.core.vo.permission import Permission, generate_user_permission_id
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id
from fanfan.core.vo.subscription import generate_subscription_id
from fanfan.core.vo.user import STAGE_CONSOLE_USER_ID, UserId, Username, UserRole
from tests.fakes.event_broker import FakeEventBroker
from tests.integration.notifications.delivered import delivered_notifications

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(
    number: int,
    title: str,
    order: float,
    *,
    is_current: bool = False,
    duration: int = 15,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=title,
        duration=duration,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=None,
    )


async def _subscribe(
    dishka_request: AsyncContainer,
    user_id: UserId,
    event: ScheduleEvent,
    *,
    lead_minutes: int = 15,
) -> Subscription:
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    subscription = Subscription(
        id=generate_subscription_id(),
        user_id=user_id,
        event_id=event.id,
        lead_minutes=lead_minutes,
    )
    await subscription_gateway.add(subscription)
    return subscription


async def _new_visitor(dishka_request: AsyncContainer, username: str) -> User:
    user_gateway = await dishka_request.get(UserGateway)
    user = User(
        id=UserId(uuid7()),
        username=Username(username),
        hashed_password=None,
        role=UserRole.VISITOR,
    )
    await user_gateway.add(user)
    return user


async def _process(
    dishka_request: AsyncContainer, uow: UnitOfWork, change: ScheduleChange
) -> None:
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    await changes_gateway.add(change)
    await uow.commit()
    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=change.id, occurred_at=datetime.now(UTC)
        )
    )


async def test_reminder_goes_out_once_when_due(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """A reminder fires once the act is within its lead time or two acts away.

    Ten-minute acts at positions 1 (current) to 5, with the default 30-second
    changeover after each. The wait for an act sums the acts from the current
    one up to it: e3 is 21 min and two acts away, e4 31.5 min, e5 42 min.
      * e3 at a 15-minute lead: outside by the clock, due by the running order;
      * e4 at a 60-minute lead: due by the clock;
      * e5 at a 15-minute lead: not due either way.
    A second change reminds nobody again.
    """
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(visitor)
    ten_minutes = 600
    events = [
        _schedule_event(n, f"Событие {n}", n, is_current=n == 1, duration=ten_minutes)
        for n in range(1, 6)
    ]
    for event in events:
        await schedule_gateway.add(event)
    await uow.commit()
    by_lead_order = await _new_visitor(dishka_request, "by_order")
    by_clock = await _new_visitor(dishka_request, "by_clock")
    not_due = await _new_visitor(dishka_request, "not_due")
    await _subscribe(dishka_request, by_lead_order.id, events[2])
    await _subscribe(dishka_request, by_clock.id, events[3], lead_minutes=60)
    await _subscribe(dishka_request, not_due.id, events[4])
    await uow.commit()

    await _process(
        dishka_request,
        uow,
        ScheduleChange.set_as_current(
            changed_event_id=events[0].id,
            previous_event_id=events[0].id,
            mailing_id=None,
            user_id=None,
        ),
    )

    delivered = await delivered_notifications(dishka_request)
    reminded = {n.user_id: n for n in delivered}
    assert set(reminded) == {by_lead_order.id, by_clock.id}
    assert reminded[by_lead_order.id].event_id == events[2].id
    assert "2 выступления" in reminded[by_lead_order.id].body
    assert "25 минут" in reminded[by_lead_order.id].body
    assert "35 минут" in reminded[by_clock.id].body
    assert all(n.type is NotificationType.SCHEDULE_SUBSCRIPTION for n in delivered)

    await _process(
        dishka_request,
        uow,
        ScheduleChange.set_as_current(
            changed_event_id=events[0].id,
            previous_event_id=events[0].id,
            mailing_id=None,
            user_id=None,
        ),
    )

    assert len(await delivered_notifications(dishka_request)) == len(delivered)


async def test_own_act_moving_is_announced_and_its_start_too(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """The subscriber hears when their act itself moves and when it starts;
    another act's change says nothing to them until theirs is due."""
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(visitor)
    hour = 3600
    current_event = _schedule_event(1, "Текущее", 1, is_current=True, duration=hour)
    event_b = _schedule_event(2, "Событие B", 2, duration=hour)
    event_c = _schedule_event(3, "Событие C", 3, duration=hour)
    event_d = _schedule_event(4, "Событие D", 4, duration=hour)
    for event in (current_event, event_b, event_c, event_d):
        await schedule_gateway.add(event)
    await uow.commit()
    other = await _new_visitor(dishka_request, "subscriber_d")
    await _subscribe(dishka_request, visitor.id, event_c)
    await _subscribe(dishka_request, other.id, event_d)
    await uow.commit()

    await _process(
        dishka_request,
        uow,
        ScheduleChange.moved(
            event_id=event_c.id,
            previous_entry_id=None,
            mailing_id=None,
            user_id=None,
            next_event_changed=False,
        ),
    )
    moved = await delivered_notifications(dishka_request)
    assert [n.user_id for n in moved] == [visitor.id]
    assert "перенесено" in moved[0].body
    assert "2 выступления" in moved[0].body
    assert moved[0].event_id == event_c.id

    current_event.unset_current()
    event_c.set_current()
    await schedule_gateway.save(current_event)
    await schedule_gateway.save(event_c)
    await _process(
        dishka_request,
        uow,
        ScheduleChange.set_as_current(
            changed_event_id=event_c.id,
            previous_event_id=current_event.id,
            mailing_id=None,
            user_id=None,
        ),
    )

    by_user = {
        n.user_id: n for n in (await delivered_notifications(dishka_request))[1:]
    }
    assert set(by_user) == {visitor.id, other.id}
    assert "началось" in by_user[visitor.id].body
    assert by_user[other.id].event_id == event_d.id
    assert "1 выступление" in by_user[other.id].body


async def test_act_removed_before_the_show_is_announced(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """With no act current yet there is no wait to estimate, but subscribers
    still hear that their act was taken out of the programme."""
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(visitor)
    event = _schedule_event(1, "Событие", 1)
    await schedule_gateway.add(event)
    await uow.commit()
    await _subscribe(dishka_request, visitor.id, event)
    await uow.commit()

    await _process(
        dishka_request,
        uow,
        ScheduleChange.skipped(
            event_id=event.id,
            mailing_id=None,
            user_id=None,
            next_event_changed=False,
        ),
    )

    delivered = await delivered_notifications(dishka_request)
    assert [n.user_id for n in delivered] == [visitor.id]
    assert "снято" in delivered[0].body


async def test_missing_durations_leave_the_reminder_to_the_running_order(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """Acts with no planned duration give no estimate: changeovers alone would
    put every act a few minutes away and remind everyone at once."""
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(visitor)
    events = [
        _schedule_event(n, f"Событие {n}", n, is_current=n == 1, duration=0)
        for n in range(1, 6)
    ]
    for event in events:
        await schedule_gateway.add(event)
    await uow.commit()
    far = await _new_visitor(dishka_request, "far")
    await _subscribe(dishka_request, visitor.id, events[2])
    await _subscribe(dishka_request, far.id, events[4])
    await uow.commit()

    await _process(
        dishka_request,
        uow,
        ScheduleChange.set_as_current(
            changed_event_id=events[0].id,
            previous_event_id=events[0].id,
            mailing_id=None,
            user_id=None,
        ),
    )

    delivered = await delivered_notifications(dishka_request)
    assert [n.user_id for n in delivered] == [visitor.id]
    assert "минут" not in delivered[0].body


async def test_schedule_change_fan_out_reuses_ids_across_redelivery(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """A redelivered schedule-change trigger mints the same notification ids.

    The trigger is delivered at-least-once, so the interactor can run twice for
    one change. The notifications insert dedups on id (on-conflict-do-nothing),
    so a rerun that produced fresh random ids would duplicate every recipient's
    notification. Running the interactor twice must yield the same id for the
    same recipient.
    """
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
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
            lead_minutes=15,
        )
    )
    change = ScheduleChange.moved(
        event_id=event_c.id,
        previous_entry_id=None,
        mailing_id=None,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    data = SendScheduleChangeNotificationsInput(
        schedule_change_id=change.id, occurred_at=datetime.now(UTC)
    )
    await interactor(data)
    await interactor(data)

    delivered = await delivered_notifications(dishka_request)
    assert len(delivered) == 2
    assert delivered[0].id == delivered[1].id


async def test_stale_schedule_change_is_dropped_and_its_mailing_failed(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """A change processed long after it was made sends nothing.

    The notifications are built from the schedule as it is now, so a change
    delivered late (after an outage) would announce the wrong event. Its mailing
    is settled as failed so it does not stay PENDING forever.
    """
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
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
            lead_minutes=15,
        )
    )
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    change = ScheduleChange.moved(
        event_id=event_c.id,
        previous_entry_id=None,
        mailing_id=mailing.id,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=change.id,
            occurred_at=datetime.now(UTC) - timedelta(hours=1),
        )
    )

    assert broker.published_events == []
    saved_mailing = await mailing_gateway.get(mailing.id)
    assert saved_mailing is not None
    assert saved_mailing.status is MailingStatus.FAILED


async def test_schedule_change_notifies_subscribers_first_and_editors_last(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """The fan-out stores and sends in chunks, so build order is delivery order.

    A subscriber's own act moving is the most time-critical; the stage
    announcement goes to every opt-in (on by default, so nearly everyone); the
    editors made the change themselves.
    """
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    subscription_gateway = await dishka_request.get(SubscriptionGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    user_gateway = await dishka_request.get(UserGateway)
    permission_gateway = await dishka_request.get(UserPermissionGateway)
    login(visitor)

    current_event = _schedule_event(1, "Текущее", 1, is_current=True)
    event_c = _schedule_event(3, "Событие C", 3)
    await schedule_gateway.add(current_event)
    await schedule_gateway.add(event_c)
    editor = User(
        id=UserId(uuid7()),
        username=Username("schedule_editor"),
        hashed_password=None,
        role=UserRole.ORGANIZER,
    )
    await user_gateway.add(editor)
    await user_gateway.add(
        User(
            id=UserId(uuid7()),
            username=Username("announcement_fan"),
            hashed_password=None,
            role=UserRole.VISITOR,
            settings=UserSettings(receive_all_announcements=True),
        )
    )
    await permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.SCHEDULE_MANAGE,
            user_id=editor.id,
        )
    )
    await uow.commit()
    await subscription_gateway.add(
        Subscription(
            id=generate_subscription_id(),
            user_id=visitor.id,
            event_id=event_c.id,
            lead_minutes=15,
        )
    )
    change = ScheduleChange.moved(
        event_id=event_c.id,
        previous_entry_id=None,
        mailing_id=None,
        user_id=editor.id,
        next_event_changed=True,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=change.id, occurred_at=datetime.now(UTC)
        )
    )

    titles = [n.title for n in await delivered_notifications(dishka_request)]
    expected_order = [
        "Выступление из подписок изменилось",
        "На сцене",
        "Изменение программы",
    ]
    kinds: list[str] = []
    for title in titles:
        if not kinds or kinds[-1] != title:
            kinds.append(title)
    assert kinds == expected_order


async def _add_schedule_editor(dishka_request: AsyncContainer, uow: UnitOfWork) -> User:
    user_gateway = await dishka_request.get(UserGateway)
    permission_gateway = await dishka_request.get(UserPermissionGateway)
    editor = User(
        id=UserId(uuid7()),
        username=Username("schedule_editor"),
        hashed_password=None,
        role=UserRole.ORGANIZER,
    )
    await user_gateway.add(editor)
    await permission_gateway.add(
        UserPermission(
            id=generate_user_permission_id(),
            permission=Permission.SCHEDULE_MANAGE,
            user_id=editor.id,
        )
    )
    await uow.commit()
    return editor


async def _notify_set_current(
    dishka_request: AsyncContainer, uow: UnitOfWork, author_id: UserId
) -> list[str]:
    """Announce a set-current change by ``author_id``; return each notice's
    recipient as "title:user_id"."""
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    current_event = _schedule_event(1, "Текущее", 1, is_current=True)
    await schedule_gateway.add(current_event)
    change = ScheduleChange.set_as_current(
        changed_event_id=current_event.id,
        previous_event_id=None,
        mailing_id=None,
        user_id=author_id,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(
        SendScheduleChangeNotificationsInput(
            schedule_change_id=change.id, occurred_at=datetime.now(UTC)
        )
    )
    return [
        f"{n.title}:{n.user_id}" for n in await delivered_notifications(dishka_request)
    ]


async def test_stage_console_edit_does_not_notify_editors(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(visitor)
    editor = await _add_schedule_editor(dishka_request, uow)

    delivered = await _notify_set_current(dishka_request, uow, STAGE_CONSOLE_USER_ID)

    assert f"Изменение программы:{editor.id}" not in delivered


async def test_human_edit_notifies_editors_but_not_the_stage_console(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    login(visitor)
    editor = await _add_schedule_editor(dishka_request, uow)

    delivered = await _notify_set_current(dishka_request, uow, editor.id)

    assert f"Изменение программы:{editor.id}" in delivered
    assert f"Изменение программы:{STAGE_CONSOLE_USER_ID}" not in delivered


async def test_abandoned_schedule_change_fails_its_mailing(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
) -> None:
    """Out of redeliveries, the handler abandons the change's fan-out so its
    mailing does not stay PENDING forever."""
    interactor = await dishka_request.get(SendScheduleChangeNotifications)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(visitor)

    event = _schedule_event(1, "Событие", 1)
    await schedule_gateway.add(event)
    mailing = Mailing.create(by_user_id=visitor.id)
    await mailing_gateway.add(mailing)
    change = ScheduleChange.moved(
        event_id=event.id,
        previous_entry_id=None,
        mailing_id=mailing.id,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor.abandon(change.id)

    saved_mailing = await mailing_gateway.get(mailing.id, lock=False)
    assert saved_mailing is not None
    assert saved_mailing.status is MailingStatus.FAILED
