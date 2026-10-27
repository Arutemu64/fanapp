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


async def _not_applied() -> bool:
    return False


async def test_edit_changes_the_served_schedule(
    dishka_request: AsyncContainer,
    schedule_editor: User,
) -> None:
    service = await dishka_request.get(ScheduleEditService)
    get_schedule = await dishka_request.get(GetSchedule)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

    async def add_event() -> None:
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

    before = await get_schedule()
    await service.edit(schedule_editor, Permission.SCHEDULE_SETUP, add_event)

    after = await get_schedule()
    assert after.etag != before.etag


async def test_failed_mutation_does_not_commit_the_announcement(
    dishka_request: AsyncContainer,
    schedule_editor: User,
) -> None:
    service = await dishka_request.get(ScheduleEditService)

    async def fail() -> ChangeFactory:
        raise EventNotFound

    with pytest.raises(EventNotFound):
        await service.announce(
            schedule_editor,
            Permission.SCHEDULE_MANAGE,
            fail,
            already_applied=_not_applied,
        )

    async def succeed() -> ChangeFactory:
        return lambda ctx: ScheduleChange.set_as_current(
            changed_event_id=None,
            previous_event_id=None,
            mailing_id=ctx.mailing_id,
            user_id=ctx.user_id,
        )

    await service.announce(
        schedule_editor,
        Permission.SCHEDULE_MANAGE,
        succeed,
        already_applied=_not_applied,
    )


async def test_already_applied_edit_skips_mutation_and_commit(
    dishka_request: AsyncContainer,
    schedule_editor: User,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = await dishka_request.get(ScheduleEditService)
    calls: list[str] = []

    async def recording_commit() -> None:
        calls.append("commit")

    monkeypatch.setattr(service.uow, "commit", recording_commit)

    async def mutate() -> ChangeFactory:
        calls.append("mutate")
        raise AssertionError

    async def applied() -> bool:
        return True

    changed = await service.announce(
        schedule_editor, Permission.SCHEDULE_MANAGE, mutate, already_applied=applied
    )

    assert changed is False

    assert calls == []
