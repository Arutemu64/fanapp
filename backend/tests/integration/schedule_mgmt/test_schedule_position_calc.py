import pytest
from dishka import AsyncContainer

from fanfan.application.dto.schedule import ScheduleEventFullDTO
from fanfan.application.ports.gateways import ScheduleEntryGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_entry import ScheduleBlockStart, ScheduleEvent
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(
    number: int,
    order: float,
    *,
    duration_seconds: int,
    is_skipped: bool = False,
    is_current: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=duration_seconds,
        order=order,
        is_current=is_current,
        is_skipped=is_skipped,
        nomination_title=None,
    )


async def test_position_with_fractional_orders(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

    first = _schedule_event(1, order=1.0, duration_seconds=10)
    second = _schedule_event(2, order=1.5, duration_seconds=20)
    skipped = _schedule_event(3, order=1.7, duration_seconds=99, is_skipped=True)
    block = ScheduleBlockStart(id=generate_schedule_entry_id(), title="Блок", order=1.8)
    third = _schedule_event(4, order=2.0, duration_seconds=30)
    for entry in (first, second, skipped, block, third):
        await schedule_gateway.add(entry)
    await uow.commit()

    schedule = (await schedule_gateway.read_schedule()).entries
    by_number = {e.number: e for e in schedule if isinstance(e, ScheduleEventFullDTO)}

    assert [e.id for e in schedule] == [
        first.id,
        second.id,
        skipped.id,
        block.id,
        third.id,
    ]
    assert by_number[1].position == 1
    assert by_number[2].position == 2
    assert by_number[4].position == 3
    assert by_number[3].position is None


async def test_schedule_names_the_current_event_once(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

    first = _schedule_event(1, order=1.0, duration_seconds=600)
    current = _schedule_event(2, order=2.0, duration_seconds=900, is_current=True)
    for entry in (first, current):
        await schedule_gateway.add(entry)
    await uow.commit()

    schedule = await schedule_gateway.read_schedule()

    assert schedule.current_event_id == current.id
    assert schedule.model_dump(mode="json")["entries"][1] == {
        "type": "event",
        "id": str(current.id),
        "number": 2,
        "title": "Событие 2",
        "duration_seconds": 900,
        "is_skipped": False,
        "nomination_title": None,
        "position": 2,
    }


async def test_schedule_without_a_current_event(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    await schedule_gateway.add(_schedule_event(1, order=1.0, duration_seconds=600))
    await uow.commit()

    schedule = await schedule_gateway.read_schedule()

    assert schedule.current_event_id is None
