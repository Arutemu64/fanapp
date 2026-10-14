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
    duration: int,
    is_skipped: bool = False,
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration=duration,
        order=order,
        is_current=False,
        is_skipped=is_skipped,
        nomination_title=None,
    )


async def test_queue_with_fractional_orders(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    # place_after averages neighbour orders, so orders are floats with gaps
    # smaller than 1. queue must stay a dense 1..N rank regardless of those gaps
    # (a RANGE window frame would frame by the order value and drop events).
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

    first = _schedule_event(1, order=1.0, duration=10)
    second = _schedule_event(2, order=1.5, duration=20)
    skipped = _schedule_event(3, order=1.7, duration=99, is_skipped=True)
    block = ScheduleBlockStart(id=generate_schedule_entry_id(), title="Блок", order=1.8)
    third = _schedule_event(4, order=2.0, duration=30)
    for entry in (first, second, skipped, block, third):
        await schedule_gateway.add(entry)
    await uow.commit()

    schedule = await schedule_gateway.read_list_schedule()
    by_number = {e.number: e for e in schedule if isinstance(e, ScheduleEventFullDTO)}

    # Skipped events and block starts are excluded from the queue numbering.
    assert [e.id for e in schedule] == [
        first.id,
        second.id,
        skipped.id,
        block.id,
        third.id,
    ]
    assert by_number[1].queue == 1
    assert by_number[2].queue == 2
    assert by_number[4].queue == 3
    assert by_number[3].queue is None
