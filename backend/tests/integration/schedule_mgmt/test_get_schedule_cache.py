from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.schedule.get_schedule import GetSchedule
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.ports.gateways import ScheduleEventGateway
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_event import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_event import generate_schedule_event_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(number: int, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_event_id(),
        number=number,
        title=f"Событие {number}",
        duration=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
        block_title=None,
    )


async def test_get_schedule_serves_cached_payload_between_reads(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
):
    interactor = await dishka_request.get(GetSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)

    await schedule_gateway.add(_schedule_event(1, 1.0))
    await uow.commit()

    first = await interactor()

    # A second, uninvalidated write must NOT change the read: a cache hit serves
    # the stored payload without touching the database.
    await schedule_gateway.add(_schedule_event(2, 2.0))
    await uow.commit()

    second = await interactor()
    assert second.etag == first.etag
    assert second.payload == first.payload
    # The stale cache still describes only the first event.
    assert '"number":2' not in second.payload


async def test_schedule_edit_invalidates_cache(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    uow: UnitOfWork,
):
    get_schedule = await dishka_request.get(GetSchedule)
    set_current = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEventGateway)
    login(schedule_editor)

    event = _schedule_event(1, 1.0)
    await schedule_gateway.add(event)
    await uow.commit()

    before = await get_schedule()  # populates the cache

    await set_current(SetCurrentScheduleEventInput(event_id=event.id))

    after = await get_schedule()
    # The edit invalidated the cache, so the read recomputed from committed state.
    assert after.etag != before.etag
    assert '"is_current":true' in after.payload
