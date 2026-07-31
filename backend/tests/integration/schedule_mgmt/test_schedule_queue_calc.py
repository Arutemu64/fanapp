import pytest
from dishka import AsyncContainer

from fanfan.application.ports.gateways import ScheduleEventGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.vo.schedule_event import generate_schedule_event_id

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
) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=duration_seconds,
        order=order,
        is_current=False,
        is_skipped=is_skipped,
        nomination_title=None,
        block_title=None,
    )


async def test_queue_with_fractional_orders(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    # place_after averages neighbour orders, so orders are floats with gaps
    # smaller than 1. queue must stay a dense 1..N rank regardless of those gaps
    # (a RANGE window frame would frame by the order value and drop events).
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)

    first = _schedule_event(1, order=1.0, duration_seconds=10)
    second = _schedule_event(2, order=1.5, duration_seconds=20)
    skipped = _schedule_event(3, order=1.7, duration_seconds=99, is_skipped=True)
    third = _schedule_event(4, order=2.0, duration_seconds=30)
    for event in (first, second, skipped, third):
        await schedule_gateway.add(event)
    await uow.commit()

    schedule = await schedule_gateway.read_list_schedule()
    by_number = {e.number: e for e in schedule}

    # Skipped events are excluded from the queue numbering.
    assert by_number[1].queue == 1
    assert by_number[2].queue == 2
    assert by_number[4].queue == 3
    assert by_number[3].queue is None
