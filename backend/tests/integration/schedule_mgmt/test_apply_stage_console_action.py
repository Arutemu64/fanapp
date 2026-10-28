from collections.abc import Callable
from datetime import timedelta

import pytest
from dishka import AsyncContainer
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from fanfan.adapters.db.models import ScheduleChangeORM
from fanfan.application.interactors.schedule_mgmt.apply_stage_console_action import (
    ApplyStageConsoleAction,
    ApplyStageConsoleActionInput,
    StageConsoleAction,
)
from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
    MoveScheduleEventInput,
)
from fanfan.application.ports.gateways import (
    ScheduleChangeGateway,
    ScheduleEntryGateway,
)
from fanfan.application.ports.gateways.user_permissions import (
    UserPermissionGateway,
)
from fanfan.application.ports.uow import UnitOfWork
from fanfan.core.exceptions.base import AccessDenied
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    ScheduleEditTooFast,
)
from fanfan.core.models.schedule_entry import ScheduleEvent
from fanfan.core.models.user import User
from fanfan.core.vo.permission import Permission
from fanfan.core.vo.schedule_change import ScheduleChangeType
from fanfan.core.vo.schedule_entry import generate_schedule_entry_id
from fanfan.core.vo.user import STAGE_CONSOLE_USER_ID

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
]


def _schedule_event(number: int, order: float) -> ScheduleEvent:
    return ScheduleEvent(
        id=generate_schedule_entry_id(),
        number=number,
        title=f"Событие {number}",
        duration_seconds=15,
        order=order,
        is_current=False,
        is_skipped=False,
        nomination_title=None,
    )


async def _add_events(
    dishka_request: AsyncContainer, uow: UnitOfWork, *numbers: int
) -> list[ScheduleEvent]:
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    events = [_schedule_event(number, number) for number in numbers]
    for event in events:
        await schedule_gateway.add(event)
    await uow.commit()
    return events


async def _expire_cooldown(dishka_request: AsyncContainer) -> None:
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
    if previous is None:
        return None
    assert isinstance(previous, ScheduleEvent)
    return previous.number


async def test_set_current_by_number_acts_as_the_service_user(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    changes_gateway = await dishka_request.get(ScheduleChangeGateway)
    (act,) = await _add_events(dishka_request, uow, 7)

    changed = await interactor(
        ApplyStageConsoleActionInput(action=StageConsoleAction.SET_CURRENT, number=7)
    )

    assert changed is True
    current = await schedule_gateway.get_current()
    assert current is not None
    assert current.id == act.id
    change = await changes_gateway.get_latest_for_event(act.id)
    assert change is not None
    assert change.type is ScheduleChangeType.SET_AS_CURRENT
    assert change.user_id == STAGE_CONSOLE_USER_ID


async def test_repeated_cue_is_unchanged_inside_the_cooldown(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    await _add_events(dishka_request, uow, 7)
    show = ApplyStageConsoleActionInput(action=StageConsoleAction.SET_CURRENT, number=7)

    await interactor(show)
    changed = await interactor(show)

    assert changed is False


async def test_another_act_inside_the_cooldown_is_rate_limited(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    await _add_events(dishka_request, uow, 7, 8)

    await interactor(
        ApplyStageConsoleActionInput(action=StageConsoleAction.SET_CURRENT, number=7)
    )
    with pytest.raises(ScheduleEditTooFast):
        await interactor(
            ApplyStageConsoleActionInput(
                action=StageConsoleAction.SET_CURRENT, number=8
            )
        )


async def test_unknown_number_is_not_found(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    await _add_events(dishka_request, uow, 7)

    with pytest.raises(EventNotFound):
        await interactor(
            ApplyStageConsoleActionInput(
                action=StageConsoleAction.SET_CURRENT, number=999
            )
        )


async def test_service_user_without_schedule_manage_is_rejected(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    perm_gateway = await dishka_request.get(UserPermissionGateway)
    await _add_events(dishka_request, uow, 7)
    grant = await perm_gateway.get_by_permission(
        user_id=STAGE_CONSOLE_USER_ID, permission=Permission.SCHEDULE_MANAGE
    )
    assert grant is not None
    await perm_gateway.delete(grant)
    await uow.commit()

    with pytest.raises(AccessDenied):
        await interactor(
            ApplyStageConsoleActionInput(
                action=StageConsoleAction.SET_CURRENT, number=7
            )
        )


async def test_skip_and_unskip(dishka_request: AsyncContainer, uow: UnitOfWork) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    schedule_gateway = await dishka_request.get(ScheduleEntryGateway)
    (act,) = await _add_events(dishka_request, uow, 7)

    await interactor(
        ApplyStageConsoleActionInput(action=StageConsoleAction.SKIP, number=7)
    )
    skipped = await schedule_gateway.get_event(act.id)
    assert skipped is not None
    assert skipped.is_skipped

    await _expire_cooldown(dishka_request)
    await interactor(
        ApplyStageConsoleActionInput(action=StageConsoleAction.UNSKIP, number=7)
    )
    unskipped = await schedule_gateway.get_event(act.id)
    assert unskipped is not None
    assert not unskipped.is_skipped


async def test_skipping_the_current_act_breaks_a_rule(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    await _add_events(dishka_request, uow, 7)
    await interactor(
        ApplyStageConsoleActionInput(action=StageConsoleAction.SET_CURRENT, number=7)
    )
    await _expire_cooldown(dishka_request)

    with pytest.raises(CurrentEventNotAllowed):
        await interactor(
            ApplyStageConsoleActionInput(action=StageConsoleAction.SKIP, number=7)
        )


async def test_move_places_the_act_after_the_number(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    first, _, _ = await _add_events(dishka_request, uow, 1, 2, 3)

    changed = await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.MOVE, number=1, after_number=2
        )
    )

    assert changed is True
    assert await _previous_number(dishka_request, first) == 2


async def test_move_after_an_unknown_number_is_not_found(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    await _add_events(dishka_request, uow, 1, 2)

    with pytest.raises(EventNotFound):
        await interactor(
            ApplyStageConsoleActionInput(
                action=StageConsoleAction.MOVE, number=1, after_number=999
            )
        )


async def test_unmove_restores_the_position(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    _, second, _ = await _add_events(dishka_request, uow, 1, 2, 3)
    await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.MOVE, number=2, after_number=3
        )
    )
    await _expire_cooldown(dishka_request)
    unmove = ApplyStageConsoleActionInput(
        action=StageConsoleAction.UNMOVE, number=2, after_number=3
    )

    assert await interactor(unmove) is True
    assert await _previous_number(dishka_request, second) == 1

    # FestEngine retrying the same event must not move the act out again.
    await _expire_cooldown(dishka_request)
    assert await interactor(unmove) is False
    assert await _previous_number(dishka_request, second) == 1


async def test_unmove_restores_the_first_act_to_the_start(
    dishka_request: AsyncContainer, uow: UnitOfWork
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    first, _ = await _add_events(dishka_request, uow, 1, 2)
    await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.MOVE, number=1, after_number=2
        )
    )
    await _expire_cooldown(dishka_request)

    await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.UNMOVE, number=1, after_number=2
        )
    )

    assert await _previous_number(dishka_request, first) is None


async def test_unmove_is_ignored_after_an_organizer_move(
    dishka_request: AsyncContainer,
    uow: UnitOfWork,
    schedule_editor: User,
    login: Callable[[User], None],
) -> None:
    interactor = await dishka_request.get(ApplyStageConsoleAction)
    organizer_move = await dishka_request.get(MoveScheduleEvent)
    *_, fourth = await _add_events(dishka_request, uow, 1, 2, 3, 4)
    await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.MOVE, number=2, after_number=3
        )
    )
    await _expire_cooldown(dishka_request)
    login(schedule_editor)
    second = await (await dishka_request.get(ScheduleEntryGateway)).get_event_by_number(
        2
    )
    assert second is not None
    await organizer_move(
        MoveScheduleEventInput(event_id=second.id, place_after_entry_id=fourth.id)
    )
    await _expire_cooldown(dishka_request)

    changed = await interactor(
        ApplyStageConsoleActionInput(
            action=StageConsoleAction.UNMOVE, number=2, after_number=3
        )
    )

    assert changed is False
    assert await _previous_number(dishka_request, second) == 4
