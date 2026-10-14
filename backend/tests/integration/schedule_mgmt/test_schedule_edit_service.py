from collections.abc import Callable

import pytest
from dishka import AsyncContainer

from fanfan.application.interactors.schedule.get_schedule import GetSchedule
from fanfan.application.ports.gateways import ScheduleEntryGateway
from fanfan.application.services.schedule_edit import (
    ChangeFactory,
    ScheduleEditService,
)
from fanfan.core.exceptions.schedule import EventNotFound
from fanfan.core.models.schedule_change import ScheduleChange
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


async def test_edit_invalidates_cache_after_commit(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = await dishka_request.get(ScheduleEditService)
    get_schedule = await dishka_request.get(GetSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    login(schedule_editor)

    async def add_event(_: User) -> None:
        await schedule_gateway.add(
            ScheduleEvent(
                id=generate_schedule_entry_id(),
                number=1,
                title="Событие",
                duration=15,
                order=1.0,
                is_current=False,
                is_skipped=False,
                nomination_title=None,
            )
        )

    # Same session on both reads, so the etag alone cannot tell invalidate-before-
    # commit from invalidate-after-commit; record the call order instead.
    calls: list[str] = []
    commit = service.uow.commit
    invalidate = service.schedule_cache.invalidate

    async def recording_commit() -> None:
        await commit()
        calls.append("commit")

    async def recording_invalidate() -> None:
        calls.append("invalidate")
        await invalidate()

    monkeypatch.setattr(service.uow, "commit", recording_commit)
    monkeypatch.setattr(service.schedule_cache, "invalidate", recording_invalidate)

    before = await get_schedule()  # populates the cache
    await service.edit(Permission.SCHEDULE_IMPORT, add_event)

    assert calls == ["commit", "invalidate"]
    after = await get_schedule()
    assert after.etag != before.etag


async def test_failed_mutation_does_not_commit_the_announcement(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    service = await dishka_request.get(ScheduleEditService)
    login(schedule_editor)

    async def fail(_: User) -> ChangeFactory:
        raise EventNotFound

    with pytest.raises(EventNotFound):
        await service.announce(Permission.SCHEDULE_MANAGE, fail)

    # No change was recorded, so the cooldown was not spent by the failed edit.
    async def succeed(_: User) -> ChangeFactory:
        return lambda ctx: ScheduleChange.set_as_current(
            changed_event_id=None,
            previous_event_id=None,
            mailing_id=ctx.mailing_id,
            user_id=ctx.user_id,
        )

    await service.announce(Permission.SCHEDULE_MANAGE, succeed)
