from collections.abc import Callable
from uuid import UUID

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
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
from fanfan.core.exceptions.schedule import EventNotFound, ScheduleEditTooFast
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
    title: str,
    order: float,
    *,
    is_current: bool = False,
    duration: int = 15,
    nomination_title: str | None = None,
    block_title: str | None = None,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=title,
        duration=duration,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=nomination_title,
        block_title=block_title,
    )


async def test_set_current_event_replaces_previous_current_and_records_change(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    mailing_gateway = await dishka_request.get(MailingGateway)
    login(schedule_editor)

    previous_current_event = _schedule_event(
        1, "Старое текущее событие", 1, is_current=True
    )
    new_current_event = _schedule_event(
        2,
        "Новое текущее событие",
        2,
        duration=20,
        nomination_title="Номинация",
        block_title="Блок",
    )
    await schedule_gateway.add(previous_current_event)
    await schedule_gateway.add(new_current_event)
    await uow.commit()

    await interactor(SetCurrentScheduleEventInput(event_id=new_current_event.id))

    saved_previous_event = await schedule_gateway.get_by_id(previous_current_event.id)
    saved_new_event = await schedule_gateway.get_by_id(new_current_event.id)
    assert saved_previous_event is not None
    assert saved_new_event is not None
    assert saved_previous_event.is_current is False
    assert saved_new_event.is_current is True

    changes = await changes_gateway.read_list_schedule_changes()
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SET_AS_CURRENT
    assert change.changed_event is not None
    assert change.changed_event.id == new_current_event.id
    assert change.argument_event is not None
    assert change.argument_event.id == previous_current_event.id
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.user.username == schedule_editor.username
    assert change.next_event_changed is True
    assert change.mailing_id is not None

    # Changing the current event creates a mailing notification from the same user.
    mailing = await mailing_gateway.get(change.mailing_id)
    assert mailing is not None
    assert mailing.by_user_id == schedule_editor.id

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_set_current_event_sets_current_when_none_was_current(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    # No event has been marked as current yet.
    event = _schedule_event(1, "Первое текущее событие", 1)
    await schedule_gateway.add(event)
    await uow.commit()

    await interactor(SetCurrentScheduleEventInput(event_id=event.id))

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.is_current is True

    changes = await changes_gateway.read_list_schedule_changes()
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SET_AS_CURRENT
    assert change.changed_event is not None
    assert change.changed_event.id == event.id
    # There was no previous current event.
    assert change.argument_event is None
    assert change.user is not None
    assert change.user.id == schedule_editor.id

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_set_current_event_can_unset_current_event(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    previous_current_event = _schedule_event(1, "Текущее событие", 1, is_current=True)
    await schedule_gateway.add(previous_current_event)
    await uow.commit()

    await interactor(SetCurrentScheduleEventInput(event_id=None))

    saved_previous_event = await schedule_gateway.get_by_id(previous_current_event.id)
    assert saved_previous_event is not None
    assert saved_previous_event.is_current is False

    changes = await changes_gateway.read_list_schedule_changes()
    assert len(changes) == 1
    change = changes[0]
    assert change.type == ScheduleChangeType.SET_AS_CURRENT
    assert change.changed_event is None
    assert change.argument_event is not None
    assert change.argument_event.id == previous_current_event.id
    assert change.user is not None
    assert change.user.id == schedule_editor.id
    assert change.next_event_changed is True
    assert change.mailing_id is not None

    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=change.id))


async def test_set_current_event_raises_when_event_not_found(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    previous_current_event = _schedule_event(1, "Текущее событие", 1, is_current=True)
    await schedule_gateway.add(previous_current_event)
    await uow.commit()

    unknown_event_id = ScheduleEventId(UUID("00000000-0000-0000-0000-000000000000"))

    with pytest.raises(EventNotFound):
        await interactor(SetCurrentScheduleEventInput(event_id=unknown_event_id))

    # Roll back the cleared current flag from the incomplete
    # transaction after the error.
    await uow.rollback()

    saved_previous_event = await schedule_gateway.get_by_id(previous_current_event.id)
    assert saved_previous_event is not None
    assert saved_previous_event.is_current is True
    assert await changes_gateway.read_list_schedule_changes() == []
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_set_current_event_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    # A regular visitor does not have the SCHEDULE_MANAGE permission.
    login(visitor)

    event = _schedule_event(1, "Событие", 1)
    await schedule_gateway.add(event)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(SetCurrentScheduleEventInput(event_id=event.id))

    saved_event = await schedule_gateway.get_by_id(event.id)
    assert saved_event is not None
    assert saved_event.is_current is False
    assert await changes_gateway.read_list_schedule_changes() == []
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []


async def test_set_current_event_twice_in_a_row_raises_too_fast(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    login(schedule_editor)

    first_event = _schedule_event(1, "Первое событие", 1)
    second_event = _schedule_event(2, "Второе событие", 2)
    await schedule_gateway.add(first_event)
    await schedule_gateway.add(second_event)
    await uow.commit()

    # The rate-limit guard for announcements uses a real Redis lock
    # (announcement_timeout from seeds — 10 seconds), which is cleared
    # between tests by the reset_redis fixture.
    await interactor(SetCurrentScheduleEventInput(event_id=first_event.id))
    with pytest.raises(ScheduleEditTooFast):
        await interactor(SetCurrentScheduleEventInput(event_id=second_event.id))

    # The second call is rejected before writing changes:
    # the first event remains current.
    saved_first_event = await schedule_gateway.get_by_id(first_event.id)
    saved_second_event = await schedule_gateway.get_by_id(second_event.id)
    assert saved_first_event is not None
    assert saved_first_event.is_current is True
    assert saved_second_event is not None
    assert saved_second_event.is_current is False

    changes = await changes_gateway.read_list_schedule_changes()
    assert len(changes) == 1
    assert [
        (m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)
    ] == as_outbox(ScheduleChangeCreated(schedule_change_id=changes[0].id))
