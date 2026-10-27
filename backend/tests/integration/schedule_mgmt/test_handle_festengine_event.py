from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from dishka import AsyncContainer
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import ScheduleChangeORM, UserPermissionORM
from fanfan.application.interactors.festengine.handle_festengine_event import (
    FestEngineAction,
    FestEngineEventInput,
    FestEngineEventOutput,
    FestEngineEventStatus,
    FestEnginePrevious,
    FestEngineRowData,
    HandleFestEngineEvent,
)
from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
    MoveScheduleEventInput,
)
from fanfan.application.ports.gateways import (
    ScheduleChangeGateway,
    ScheduleEntryGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    SameEventsAreNotAllowed,
    ScheduleEditTooFast,
)
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id
from fanfan.core.vo.user import SYSTEM_USER_ID

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]

UPDATED_SET_CURRENT = FestEngineEventOutput(
    status=FestEngineEventStatus.UPDATED, actions=[FestEngineAction.SET_CURRENT]
)
UNCHANGED = FestEngineEventOutput(status=FestEngineEventStatus.UNCHANGED, actions=[])


def _event(number: int, order: float, *, is_current: bool = False) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Номер {number}",
        duration=5,
        order=order,
        is_current=is_current,
        is_skipped=False,
        nomination_title=None,
    )


def _cue(
    num: str, *, row_type: str = "track", age_seconds: int = 0
) -> FestEngineEventInput:
    return FestEngineEventInput(
        type="row.play",
        timestamp=datetime.now(UTC) - timedelta(seconds=age_seconds),
        data=FestEngineRowData(num=num, row_type=row_type, notes=""),
    )


def _note_edit(num: str, previous: str, current: str) -> FestEngineEventInput:
    return FestEngineEventInput(
        type="row.updated",
        timestamp=datetime.now(UTC),
        data=FestEngineRowData(
            num=num,
            row_type="track",
            notes=current,
            previous=FestEnginePrevious(notes=previous),
        ),
    )


async def _add_events(
    dishka_request: AsyncContainer, uow: UnitOfWork, *events: ScheduleEvent
) -> None:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    for event in events:
        await schedule_gateway.add(event)
    await uow.commit()


async def _pass_cooldown(dishka_request: AsyncContainer) -> None:
    session = await dishka_request.get(AsyncSession)
    await session.execute(
        update(ScheduleChangeORM).values(
            created_at=ScheduleChangeORM.created_at - timedelta(hours=1)
        )
    )


async def _previous_number(
    dishka_request: AsyncContainer, event: ScheduleEvent
) -> int | None:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    saved = await schedule_gateway.get_event(event.id)
    assert saved is not None
    previous = await schedule_gateway.get_previous_by_order(saved.order)
    if previous is None or not isinstance(previous, ScheduleEvent):
        return None
    return previous.number


async def test_cue_sets_the_act_current_as_the_system_user(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(7, 1)
    await _add_events(dishka_request, uow, act)

    result = await handle(_cue("007"))

    assert result == UPDATED_SET_CURRENT
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    current = await schedule_gateway.get_current()
    assert current is not None
    assert current.id == act.id
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    change = await changes_gateway.get_latest_for_event(act.id)
    assert change is not None
    assert change.type is ScheduleChangeType.SET_AS_CURRENT
    assert change.user_id == SYSTEM_USER_ID


async def test_dup_row_cue_sets_the_source_act_current(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(183, 1))

    result = await handle(_cue("183", row_type="dup"))

    assert result == UPDATED_SET_CURRENT


async def test_repeated_cue_is_a_no_op_inside_the_cooldown(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(5, 1))

    await handle(_cue("005"))
    result = await handle(_cue("005"))

    assert result == UNCHANGED


async def test_cue_for_another_act_inside_the_cooldown_is_rate_limited(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(1, 1), _event(2, 2))

    await handle(_cue("001"))
    with pytest.raises(ScheduleEditTooFast):
        await handle(_cue("002"))


async def test_cue_for_an_unknown_number_raises_not_found(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(1, 1))

    with pytest.raises(EventNotFound):
        await handle(_cue("999"))


async def test_stale_cue_changes_nothing(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(1, 1))

    result = await handle(_cue("001", age_seconds=61))

    assert result.status is FestEngineEventStatus.STALE
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    assert await schedule_gateway.get_current() is None


@pytest.mark.parametrize(
    "event",
    [
        FestEngineEventInput(type="hook.test", timestamp=datetime.now(UTC)),
        FestEngineEventInput(
            type="row.end",
            timestamp=datetime.now(UTC),
            data=FestEngineRowData(num="001", row_type="track"),
        ),
        FestEngineEventInput(
            type="row.show",
            timestamp=datetime.now(UTC),
            data=FestEngineRowData(num=None, row_type="countdown"),
        ),
    ],
)
async def test_irrelevant_events_are_ignored(
    dishka_request: AsyncContainer, event: FestEngineEventInput
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)

    result = await handle(event)

    assert result.status is FestEngineEventStatus.IGNORED


async def test_system_user_without_schedule_manage_is_rejected(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(1, 1))
    session = await dishka_request.get(AsyncSession)
    await session.execute(
        delete(UserPermissionORM).where(
            UserPermissionORM.user_id == SYSTEM_USER_ID,
            UserPermissionORM.permission == Permission.SCHEDULE_MANAGE,
        )
    )

    with pytest.raises(AccessDenied):
        await handle(_cue("001"))


async def test_skip_and_unskip_follow_the_leading_dash(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(4, 1)
    await _add_events(dishka_request, uow, act)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)

    skipped = await handle(_note_edit("004", "", "- заболел"))
    saved = await schedule_gateway.get_event(act.id)
    assert saved is not None
    assert saved.is_skipped is True

    await _pass_cooldown(dishka_request)
    unskipped = await handle(_note_edit("004", "- заболел", "выздоровел"))
    saved = await schedule_gateway.get_event(act.id)
    assert saved is not None
    assert saved.is_skipped is False

    assert skipped.actions == [FestEngineAction.SKIP]
    assert unskipped.actions == [FestEngineAction.UNSKIP]


async def test_skipping_the_current_act_is_refused(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(4, 1, is_current=True))

    with pytest.raises(CurrentEventNotAllowed):
        await handle(_note_edit("004", "", "-"))


async def test_unrelated_note_edit_is_unchanged(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(4, 1))

    result = await handle(_note_edit("004", "свет синий", "свет красный"))

    assert result == UNCHANGED


async def test_move_places_the_act_after_the_target(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(100, 1)
    await _add_events(dishka_request, uow, act, _event(200, 2), _event(305, 3))

    result = await handle(_note_edit("100", "", ">305 maybe"))

    assert result.actions == [FestEngineAction.MOVE]
    assert await _previous_number(dishka_request, act) == 305


async def test_move_to_a_missing_number_uses_the_closest_lower_one(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(100, 1)
    await _add_events(dishka_request, uow, act, _event(200, 2), _event(310, 3))

    await handle(_note_edit("100", "", ">305"))

    assert await _previous_number(dishka_request, act) == 200


async def test_move_with_nothing_below_the_target_raises_not_found(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(400, 1), _event(500, 2))

    with pytest.raises(EventNotFound):
        await handle(_note_edit("500", "", ">305"))


async def test_move_after_itself_is_refused(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    await _add_events(dishka_request, uow, _event(100, 1), _event(305, 2))

    with pytest.raises(SameEventsAreNotAllowed):
        await handle(_note_edit("305", "", ">305"))


async def test_unmove_puts_the_act_back(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(150, 2)
    await _add_events(
        dishka_request, uow, _event(100, 1), act, _event(200, 3), _event(305, 4)
    )

    await handle(_note_edit("150", "", ">305"))
    await _pass_cooldown(dishka_request)
    result = await handle(_note_edit("150", ">305", ""))

    assert result.actions == [FestEngineAction.UNMOVE]
    assert await _previous_number(dishka_request, act) == 100


async def test_unmove_of_the_first_act_puts_it_first_again(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(100, 1)
    await _add_events(dishka_request, uow, act, _event(305, 2))

    await handle(_note_edit("100", "", ">305"))
    await _pass_cooldown(dishka_request)
    await handle(_note_edit("100", ">305", ""))

    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    first = await schedule_gateway.get_first()
    assert first is not None
    assert first.id == act.id


async def test_unmove_leaves_an_organizers_later_move_alone(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    move = await dishka_request.get(MoveScheduleEvent)
    login(schedule_editor)
    first = _event(100, 1)
    act = _event(150, 2)
    target = _event(305, 3)
    await _add_events(dishka_request, uow, first, act, target)

    await handle(_note_edit("150", "", ">305"))
    await _pass_cooldown(dishka_request)
    await move(MoveScheduleEventInput(event_id=act.id, place_after_entry_id=None))
    await _pass_cooldown(dishka_request)
    result = await handle(_note_edit("150", ">305", ""))

    assert result == UNCHANGED
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    top = await schedule_gateway.get_first()
    assert top is not None
    assert top.id == act.id


async def test_skip_and_move_in_one_edit_retry_through_the_cooldown(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    handle = await dishka_request.get(HandleFestEngineEvent)
    act = _event(100, 1)
    await _add_events(dishka_request, uow, act, _event(305, 2))
    edit = _note_edit("100", "", "->305")

    with pytest.raises(ScheduleEditTooFast):
        await handle(edit)
    await _pass_cooldown(dishka_request)
    retried = await handle(edit)

    assert retried.actions == [FestEngineAction.MOVE]
    assert await _previous_number(dishka_request, act) == 305
