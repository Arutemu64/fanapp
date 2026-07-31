from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
    ScheduleEntry,
)
from fanfan.application.ports.gateways import ScheduleEventGateway
from fanfan.application.ports.gateways.outbox import OutboxGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_event import generate_schedule_event_id
from tests.fakes.realtime_gateway import FakeRealtimeGateway
from tests.integration.conftest import as_outbox

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _entry(number: int, title: str) -> ScheduleEntry:
    return ScheduleEntry(
        number=number,
        title=title,
        duration_seconds=15,
        nomination_title=f"Номинация {number}",
        block_title=f"Блок {number}",
    )


def _schedule_event(number: int, title: str, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=title,
        duration_seconds=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_import_creates_events_on_empty_schedule(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    outbox: OutboxGateway,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ImportSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    login(schedule_editor)

    await interactor(
        ImportScheduleInput(
            schedule=[
                _entry(1, "Открытие"),
                _entry(2, "Концерт"),
                _entry(3, "Закрытие"),
            ]
        )
    )

    schedule = await schedule_gateway.list_all()
    by_number = {e.number: e for e in schedule}
    assert set(by_number) == {1, 2, 3}
    assert by_number[1].title == "Открытие"
    assert by_number[2].title == "Концерт"
    assert by_number[3].title == "Закрытие"
    assert by_number[1].nomination_title == "Номинация 1"
    assert by_number[1].block_title == "Блок 1"

    # Orders are assigned in list order with a fixed step, so imported events
    # keep their given sequence.
    assert by_number[1].order < by_number[2].order < by_number[3].order

    # Import records no schedule change and enqueues no events.
    assert [(m.subject, m.payload) for m in await outbox.fetch_unpublished(1000)] == []

    # Because there is no outbox event, the SSE broadcast telling every other
    # client to refetch has to come from the interactor itself. Broadcast, not
    # targeted at the importing user — the schedule is shared state.
    assert realtime.published == [(None, SSEMessage(SSEEventName.SCHEDULE_UPDATED))]


async def test_import_updates_existing_and_deletes_orphans(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ImportSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    login(schedule_editor)

    # An event matched by number is updated in place (id preserved); one that
    # is not in the import is treated as orphaned and deleted.
    existing = _schedule_event(1, "Старое название", 100.0)
    orphan = _schedule_event(2, "Больше не в расписании", 200.0)
    await schedule_gateway.add(existing)
    await schedule_gateway.add(orphan)
    await uow.commit()

    await interactor(
        ImportScheduleInput(
            schedule=[
                _entry(1, "Новое название"),
                _entry(3, "Новое событие"),
            ]
        )
    )

    schedule = await schedule_gateway.list_all()
    by_number = {e.number: e for e in schedule}
    assert set(by_number) == {1, 3}

    # Matched event keeps its identity but takes the imported details.
    assert by_number[1].id == existing.id
    assert by_number[1].title == "Новое название"
    # New event is added.
    assert by_number[3].title == "Новое событие"
    # Orphan is gone.
    assert await schedule_gateway.get_by_id(orphan.id) is None


async def test_import_without_permission_raises_access_denied(
    dishka_request: AsyncContainer,
    visitor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(ImportSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)
    # A regular visitor does not have the SCHEDULE_IMPORT permission.
    login(visitor)

    existing = _schedule_event(1, "Существующее событие", 100.0)
    await schedule_gateway.add(existing)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(ImportScheduleInput(schedule=[_entry(2, "Новое")]))

    # The schedule is left exactly as it was.
    schedule = await schedule_gateway.list_all()
    assert [e.number for e in schedule] == [1]
    assert await schedule_gateway.get_by_id(existing.id) is not None
    # A rejected import must not send every client off to refetch.
    assert realtime.published == []
