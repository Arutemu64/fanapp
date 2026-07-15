from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
    MoveScheduleEventInput,
)
from fanfan.application.ports.gateways import (
    ScheduleChangeGateway,
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.schedule import ScheduleChangeCreated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.schedule import (
    EventNotFound,
    SameEventsAreNotAllowed,
    ScheduleEditTooFast,
)
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_event import (
    ScheduleEventId,
    generate_schedule_event_id,
)
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(
    number: int,
    order: float,
    *,
    is_current: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration=15,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_move_reorders_event_and_records_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    # No event is current, so get_next() sees nothing and the queue never
    # changes: next_event_changed must stay False.
    first = _schedule_event(1, 1)
    second = _schedule_event(2, 2)
    third = _schedule_event(3, 3)
    for event in (first, second, third):
        await schedule_gateway.add(event)
    await uow.commit()

    await interactor(
        MoveScheduleEventInput(
            event_id=first.id,
            place_after_event_id=second.id,
        )
    )

    # place_after averages the neighbour orders: (2 + 3) / 2.
    saved_first = await schedule_gateway.get_by_id(first.id)
    assert saved_first is not None
    assert saved_first.order == 2.5

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=Pagination(limit=100, offset=0)
    )
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.MOVED
    assert change.changed_event is not None
    assert change.changed_event.id == first.id
    # The moved event had no event before it in order, so there is no anchor
    # to record for undo.
    assert change.argument_event is None
    assert change.next_event_changed is False
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.mailing_id is not None

    mailing = await mailing_gateway.get(change.mailing_id)
    assert mailing is not None
    assert mailing.by_user_id == schedule_editor.id

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_move_records_previous_event_and_next_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    # With a current event, the next event is the first one after it by order.
    current = _schedule_event(1, 1, is_current=True)
    second = _schedule_event(2, 2)
    third = _schedule_event(3, 3)
    for event in (current, second, third):
        await schedule_gateway.add(event)
    await uow.commit()

    # Move "second" to the very end: the next event after "current" changes
    # from "second" to "third".
    await interactor(
        MoveScheduleEventInput(
            event_id=second.id,
            place_after_event_id=third.id,
        )
    )

    # Placed after the last event, so its order is last_order + 1.
    saved_second = await schedule_gateway.get_by_id(second.id)
    assert saved_second is not None
    assert saved_second.order == 4

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=Pagination(limit=100, offset=0)
    )
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.MOVED
    assert change.changed_event is not None
    assert change.changed_event.id == second.id
    # "current" was the only event before "second" in order, so it is recorded
    # as the anchor to restore on undo.
    assert change.argument_event is not None
    assert change.argument_event.id == current.id
    assert change.next_event_changed is True

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_move_event_after_itself_raises(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1)
    other = _schedule_event(2, 2)
    await schedule_gateway.add(event)
    await schedule_gateway.add(other)
    await uow.commit()

    with pytest.raises(SameEventsAreNotAllowed):
        await interactor(
            MoveScheduleEventInput(
                event_id=event.id,
                place_after_event_id=event.id,
            )
        )
    await uow.rollback()

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.order == 1
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=Pagination(limit=100, offset=0)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_move_raises_when_moved_event_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    anchor = _schedule_event(1, 1)
    await schedule_gateway.add(anchor)
    await uow.commit()

    unknown_event_id = ScheduleEventId(UUID("00000000-0000-0000-0000-000000000000"))
    with pytest.raises(EventNotFound):
        await interactor(
            MoveScheduleEventInput(
                event_id=unknown_event_id,
                place_after_event_id=anchor.id,
            )
        )
    await uow.rollback()

    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=Pagination(limit=100, offset=0)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_move_raises_when_target_event_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1)
    await schedule_gateway.add(event)
    await uow.commit()

    unknown_event_id = ScheduleEventId(UUID("00000000-0000-0000-0000-000000000000"))
    with pytest.raises(EventNotFound):
        await interactor(
            MoveScheduleEventInput(
                event_id=event.id,
                place_after_event_id=unknown_event_id,
            )
        )
    await uow.rollback()

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.order == 1
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=Pagination(limit=100, offset=0)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_move_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    # A regular visitor does not have the SCHEDULE_MANAGE permission.
    login(visitor)

    first = _schedule_event(1, 1)
    second = _schedule_event(2, 2)
    await schedule_gateway.add(first)
    await schedule_gateway.add(second)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(
            MoveScheduleEventInput(
                event_id=first.id,
                place_after_event_id=second.id,
            )
        )

    saved_first = await schedule_gateway.get_by_id(first.id)
    assert saved_first is not None
    assert saved_first.order == 1
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=Pagination(limit=100, offset=0)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_move_twice_in_a_row_raises_too_fast(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(MoveScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    first = _schedule_event(1, 1)
    second = _schedule_event(2, 2)
    third = _schedule_event(3, 3)
    fourth = _schedule_event(4, 4)
    for event in (first, second, third, fourth):
        await schedule_gateway.add(event)
    await uow.commit()

    # The same real-Redis rate lock as set_current guards announcements
    # (announcement_timeout from seeds), so a second move within the window
    # is rejected.
    await interactor(
        MoveScheduleEventInput(
            event_id=first.id,
            place_after_event_id=second.id,
        )
    )
    with pytest.raises(ScheduleEditTooFast):
        await interactor(
            MoveScheduleEventInput(
                event_id=third.id,
                place_after_event_id=fourth.id,
            )
        )

    # The second move is rejected before writing: "third" keeps its order and
    # only the first change is recorded.
    saved_third = await schedule_gateway.get_by_id(third.id)
    assert saved_third is not None
    assert saved_third.order == 3

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=Pagination(limit=100, offset=0)
    )
    assert len(changes) == 1
    assert changes[0].changed_event is not None
    assert changes[0].changed_event.id == first.id
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=changes[0].id))
