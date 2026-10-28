from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.page import CursorPagination
from fanfan.application.interactors.schedule_mgmt.update_schedule_event_skip import (
    UpdateScheduleEventSkip,
    UpdateScheduleEventSkipInput,
)
from fanfan.application.ports.gateways import (
    ScheduleChangeGateway,
    ScheduleEntryGateway,
)
from fanfan.application.ports.gateways.mailings import MailingGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.events.schedule import ScheduleChangeCreated
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_entry import (
    ScheduleEntryId,
    generate_schedule_entry_id,
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
    is_skipped: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=15,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
    )


async def test_skip_marks_event_and_records_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    current = _schedule_event(1, 1, is_current=True)
    second = _schedule_event(2, 2)
    third = _schedule_event(3, 3)
    for event in (current, second, third):
        await schedule_gateway.add(event)
    await uow.commit()

    await interactor(UpdateScheduleEventSkipInput(event_id=second.id, is_skipped=True))

    saved_second = await schedule_gateway.get_event(second.id)
    assert saved_second is not None
    assert saved_second.is_skipped is True

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=CursorPagination(limit=100)
    )
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SKIPPED
    assert change.changed_event is not None
    assert change.changed_event.id == second.id
    assert change.related_entry is None
    assert change.next_event_changed is True
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.mailing_id is not None

    mailing = await mailing_gateway.get(change.mailing_id)
    assert mailing is not None
    assert mailing.by_user_id == schedule_editor.id

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_unskip_marks_event_and_records_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1, is_skipped=True)
    await schedule_gateway.add(event)
    await uow.commit()

    await interactor(UpdateScheduleEventSkipInput(event_id=event.id, is_skipped=False))

    saved_event = await schedule_gateway.get_event(event.id)
    assert saved_event is not None
    assert saved_event.is_skipped is False

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=CursorPagination(limit=100)
    )
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.UNSKIPPED
    assert change.changed_event is not None
    assert change.changed_event.id == event.id
    assert change.next_event_changed is False
    assert change.user is not None
    assert change.user.id == schedule_editor.id

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_skip_current_event_raises_and_records_nothing(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    current = _schedule_event(1, 1, is_current=True)
    await schedule_gateway.add(current)
    await uow.commit()

    with pytest.raises(CurrentEventNotAllowed):
        await interactor(
            UpdateScheduleEventSkipInput(event_id=current.id, is_skipped=True)
        )
    await uow.rollback()

    saved_current = await schedule_gateway.get_event(current.id)
    assert saved_current is not None
    assert saved_current.is_skipped is False
    assert saved_current.is_current is True
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=CursorPagination(limit=100)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_skip_raises_when_event_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    unknown_event_id = ScheduleEntryId(UUID("00000000-0000-0000-0000-000000000000"))
    with pytest.raises(EventNotFound):
        await interactor(
            UpdateScheduleEventSkipInput(event_id=unknown_event_id, is_skipped=True)
        )
    await uow.rollback()

    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=CursorPagination(limit=100)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_skip_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(visitor)

    event = _schedule_event(1, 1)
    await schedule_gateway.add(event)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(
            UpdateScheduleEventSkipInput(event_id=event.id, is_skipped=True)
        )

    saved_event = await schedule_gateway.get_event(event.id)
    assert saved_event is not None
    assert saved_event.is_skipped is False
    assert (
        await changes_gateway.read_list_schedule_changes(
            pagination=CursorPagination(limit=100)
        )
        == []
    )
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_skip_twice_in_a_row_raises_too_fast(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    first = _schedule_event(1, 1)
    second = _schedule_event(2, 2)
    await schedule_gateway.add(first)
    await schedule_gateway.add(second)
    await uow.commit()

    await interactor(UpdateScheduleEventSkipInput(event_id=first.id, is_skipped=True))
    with pytest.raises(ScheduleEditTooFast):
        await interactor(
            UpdateScheduleEventSkipInput(event_id=second.id, is_skipped=True)
        )

    saved_second = await schedule_gateway.get_event(second.id)
    assert saved_second is not None
    assert saved_second.is_skipped is False

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=CursorPagination(limit=100)
    )
    assert len(changes) == 1
    assert changes[0].changed_event is not None
    assert changes[0].changed_event.id == first.id
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=changes[0].id))


async def test_skip_repeat_is_a_no_op_inside_the_cooldown(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(UpdateScheduleEventSkip)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1)
    await schedule_gateway.add(event)
    await uow.commit()

    data = UpdateScheduleEventSkipInput(event_id=event.id, is_skipped=True)
    await interactor(data)
    await interactor(data)

    changes = await changes_gateway.read_list_schedule_changes(
        pagination=CursorPagination(limit=100)
    )
    assert len(changes) == 1
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=changes[0].id))
