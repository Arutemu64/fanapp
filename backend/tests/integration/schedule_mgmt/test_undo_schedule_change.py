from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.schedule_mgmt.undo_schedule_change import (
    UndoScheduleChange,
    UndoScheduleChangeInput,
)
from fanfan.application.ports.gateways import (
    ScheduleChangeGateway,
    ScheduleEventGateway,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.schedule import ScheduleChangeCreated, ScheduleChangeUndone
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.schedule import (
    OutdatedScheduleChange,
    ScheduleChangeNotFound,
)
from fanfan.core.models.mailing import Mailing
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import (
    ScheduleChangeId,
    generate_schedule_change_id,
)
from fanfan.core.vo.schedule_event import generate_schedule_event_id
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
    is_skipped: bool = False,
    actual_start_time: datetime | None = None,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration=15,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
        block_title=None,
        actual_start_time=actual_start_time,
    )


async def test_undo_skipped_change_unskips_event(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1, is_skipped=True)
    await schedule_gateway.add(event)
    mailing = Mailing.create(by_user_id=schedule_editor.id)
    await mailing_gateway.add(mailing)
    change = ScheduleChange.skipped(
        event_id=event.id,
        mailing_id=mailing.id,
        user_id=schedule_editor.id,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.is_skipped is False

    # The change is consumed by the undo.
    assert await changes_gateway.get_by_id(change.id) is None
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=Pagination(limit=100, offset=0)
        )
        == []
    )

    # Outbox holds the setup's created event plus the undo event, in order.
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        ScheduleChangeCreated(schedule_change_id=change.id),
        ScheduleChangeUndone(mailing_id=mailing.id),
    )


async def test_undo_unskipped_change_skips_event(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1, is_skipped=False)
    await schedule_gateway.add(event)
    mailing = Mailing.create(by_user_id=schedule_editor.id)
    await mailing_gateway.add(mailing)
    change = ScheduleChange.unskipped(
        event_id=event.id,
        mailing_id=mailing.id,
        user_id=schedule_editor.id,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.is_skipped is True
    assert await changes_gateway.get_by_id(change.id) is None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        ScheduleChangeCreated(schedule_change_id=change.id),
        ScheduleChangeUndone(mailing_id=mailing.id),
    )


async def test_undo_moved_change_places_event_back_on_top(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    first = _schedule_event(1, 1)
    moved = _schedule_event(2, 2)
    third = _schedule_event(3, 3)
    for event in (first, moved, third):
        await schedule_gateway.add(event)
    mailing = Mailing.create(by_user_id=schedule_editor.id)
    await mailing_gateway.add(mailing)
    # A MOVED change with no previous event: undo puts the event back on top,
    # ahead of the current first event.
    change = ScheduleChange.moved(
        event_id=moved.id,
        previous_event_id=None,
        mailing_id=mailing.id,
        user_id=schedule_editor.id,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))

    # place_before_first sets order to (first event order - 1), so the moved
    # event now sorts ahead of everything else.
    saved_moved = await schedule_gateway.get_by_id(moved.id)
    assert saved_moved is not None
    assert saved_moved.order == 0
    assert await changes_gateway.get_by_id(change.id) is None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        ScheduleChangeCreated(schedule_change_id=change.id),
        ScheduleChangeUndone(mailing_id=mailing.id),
    )


async def test_undo_set_as_current_restores_previous_event(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    # "previous" ran earlier (it keeps its original start anchor), then
    # "changed" was set as current.
    anchor = datetime(2026, 7, 15, 12, 0, tzinfo=UTC)
    previous = _schedule_event(1, 1, actual_start_time=anchor)
    changed = _schedule_event(2, 2, is_current=True)
    await schedule_gateway.add(previous)
    await schedule_gateway.add(changed)
    mailing = Mailing.create(by_user_id=schedule_editor.id)
    await mailing_gateway.add(mailing)
    change = ScheduleChange.set_as_current(
        changed_event_id=changed.id,
        previous_event_id=previous.id,
        mailing_id=mailing.id,
        user_id=schedule_editor.id,
    )
    await changes_gateway.add(change)
    await uow.commit()

    await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))

    saved_changed = await schedule_gateway.get_by_id(changed.id)
    saved_previous = await schedule_gateway.get_by_id(previous.id)
    assert saved_changed is not None
    assert saved_previous is not None
    # Current is handed back to the previously-current event.
    assert saved_changed.is_current is False
    assert saved_previous.is_current is True
    # The restored event keeps its original start anchor rather than being
    # re-stamped with the undo moment.
    assert saved_previous.actual_start_time == anchor
    assert await changes_gateway.get_by_id(change.id) is None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(
        ScheduleChangeCreated(schedule_change_id=change.id),
        ScheduleChangeUndone(mailing_id=mailing.id),
    )


async def test_undo_set_as_current_raises_when_current_moved_on(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    # The change made "changed" current, but the schedule has since moved on:
    # a different event is current now, so the undo is outdated.
    changed = _schedule_event(1, 1, is_current=False)
    now_current = _schedule_event(2, 2, is_current=True)
    await schedule_gateway.add(changed)
    await schedule_gateway.add(now_current)
    change = ScheduleChange.set_as_current(
        changed_event_id=changed.id,
        previous_event_id=None,
        mailing_id=None,
        user_id=schedule_editor.id,
    )
    await changes_gateway.add(change)
    await uow.commit()

    with pytest.raises(OutdatedScheduleChange):
        await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))
    await uow.rollback()

    # Nothing is reverted and the change is preserved for a later, valid undo.
    saved_now_current = await schedule_gateway.get_by_id(now_current.id)
    assert saved_now_current is not None
    assert saved_now_current.is_current is True
    assert await changes_gateway.get_by_id(change.id) is not None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_undo_raises_when_change_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    login(schedule_editor)

    unknown_change_id = ScheduleChangeId(UUID("00000000-0000-0000-0000-000000000000"))
    with pytest.raises(ScheduleChangeNotFound):
        await interactor(UndoScheduleChangeInput(schedule_change_id=unknown_change_id))

    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_undo_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(UndoScheduleChange)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    # A regular visitor does not have the SCHEDULE_MANAGE permission.
    login(visitor)

    event = _schedule_event(1, 1, is_skipped=True)
    await schedule_gateway.add(event)
    change = ScheduleChange.skipped(
        event_id=event.id,
        mailing_id=None,
        user_id=None,
        next_event_changed=False,
    )
    await changes_gateway.add(change)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(UndoScheduleChangeInput(schedule_change_id=change.id))

    # The change is untouched: permission is checked before anything is reverted.
    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.is_skipped is True
    assert await changes_gateway.get_by_id(change.id) is not None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))
