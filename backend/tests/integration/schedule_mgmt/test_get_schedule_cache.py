from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.dto.realtime import SSEEventName, SSEMessage
from fanfan.application.interactors.schedule.get_schedule import GetSchedule
from fanfan.application.interactors.schedule.publish_schedule_updated import (
    PublishScheduleUpdated,
)
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.ports.gateways import ScheduleEntryGateway
from fanfan.application.ports.schedule_cache import (
    CachedSchedule,
    ScheduleCacheGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id
from fanfan.core.vo.user import UserId
from tests.fakes.realtime_gateway import FakeRealtimeGateway

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(number: int, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
    )


async def test_get_schedule_serves_cached_payload_between_reads(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
) -> None:
    interactor = await dishka_request.get(GetSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

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
) -> None:
    get_schedule = await dishka_request.get(GetSchedule)
    set_current = await dishka_request.get(SetCurrentScheduleEvent)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
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


async def test_publish_schedule_updated_warms_cache_before_broadcast(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_schedule = await dishka_request.get(GetSchedule)
    publish = await dishka_request.get(PublishScheduleUpdated)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    schedule_cache = await dishka_request.get(ScheduleCacheGateway)
    realtime = await dishka_request.get(FakeRealtimeGateway)

    await schedule_gateway.add(_schedule_event(1, 1.0))
    await uow.commit()
    stale = await get_schedule()  # populates the cache

    # Left stale on purpose: the warm-up must overwrite the entry from
    # committed state, not keep whatever the cache already holds.
    await schedule_gateway.add(_schedule_event(2, 2.0))
    await uow.commit()

    # Read the cache at the moment of the broadcast: checking it after publish()
    # returns would also pass if the broadcast went out before the warm-up.
    cached_at_broadcast: list[CachedSchedule | None] = []
    record_broadcast = realtime.publish

    async def publish_and_snapshot(
        message: SSEMessage, user_id: UserId | None = None
    ) -> None:
        cached_at_broadcast.append(await schedule_cache.get())
        await record_broadcast(message, user_id)

    monkeypatch.setattr(realtime, "publish", publish_and_snapshot)

    await publish()

    assert realtime.published == [(None, SSEMessage(SSEEventName.SCHEDULE_UPDATED))]
    [warmed] = cached_at_broadcast
    assert warmed is not None
    assert warmed.etag != stale.etag
    assert '"number":2' in warmed.payload
