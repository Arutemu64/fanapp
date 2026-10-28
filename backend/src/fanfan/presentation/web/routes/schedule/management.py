from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path
from pydantic import MISSING

from fanfan.application.interactors.schedule_mgmt.move_schedule_event import (
    MoveScheduleEvent,
    MoveScheduleEventInput,
)
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventInput,
)
from fanfan.application.interactors.schedule_mgmt.update_schedule_event_skip import (
    UpdateScheduleEventSkip,
    UpdateScheduleEventSkipInput,
)
from fanfan.core.vo.schedule_entry import ScheduleEntryId
from fanfan.presentation.web.responses import AUTH_RESPONSES, RATE_LIMIT_RESPONSES
from fanfan.presentation.web.schemas.error import ProblemDetails
from fanfan.presentation.web.schemas.schedule import (
    SetCurrentScheduleEventBody,
    UpdateScheduleEventBody,
)
from fanfan.presentation.web.security import session_security

management_router = APIRouter(
    dependencies=[session_security],
    responses={**AUTH_RESPONSES, **RATE_LIMIT_RESPONSES},
)


@management_router.put(
    "/current",
    status_code=204,
    summary="Set specific event as current",
    description="Updates the schedule state to mark a specific event as active. "
    "Validates timing and event status. "
    "If that event is already current, nothing is changed or announced.",
    responses={
        204: {"description": "Event set as current successfully."},
        400: {
            "model": ProblemDetails,
            "description": "Event is skipped or invalid for this operation.",
        },
        404: {"model": ProblemDetails, "description": "Event ID not found."},
    },
)
@inject
async def set_current_event(
    data: SetCurrentScheduleEventBody,
    interactor: FromDishka[SetCurrentScheduleEvent],
) -> None:
    await interactor(SetCurrentScheduleEventInput(event_id=data.event_id))


@management_router.delete(
    "/current",
    status_code=204,
    summary="Unset current schedule event",
    description="Clears the currently active event from the schedule. "
    "Subject to rate limiting. If no event is current, nothing is announced.",
    responses={
        204: {"description": "Current event cleared successfully."},
    },
)
@inject
async def clear_current_event(
    interactor: FromDishka[SetCurrentScheduleEvent],
) -> None:
    await interactor(SetCurrentScheduleEventInput(event_id=None))


@management_router.patch(
    "/{event_id}",
    status_code=204,
    summary="Update a schedule event",
    description="Applies one change per request. `is_skipped` skips the event or "
    "restores it; the current event cannot be skipped. `place_after_entry_id` moves "
    "the event right after that entry, or to the top when null. "
    "Requesting the state that already holds changes and announces nothing.",
    responses={
        204: {"description": "Event updated successfully."},
        400: {
            "model": ProblemDetails,
            "description": "The current event cannot be skipped, "
            "or the event cannot be placed after itself.",
        },
        404: {
            "model": ProblemDetails,
            "description": "Event or target entry not found.",
        },
    },
)
@inject
async def update_schedule_event(
    event_id: Annotated[ScheduleEntryId, Path(description="Schedule event ID.")],
    data: UpdateScheduleEventBody,
    skip: FromDishka[UpdateScheduleEventSkip],
    move: FromDishka[MoveScheduleEvent],
) -> None:
    if data.is_skipped is not MISSING:
        await skip(
            UpdateScheduleEventSkipInput(event_id=event_id, is_skipped=data.is_skipped)
        )
        return
    if data.place_after_entry_id is not MISSING:
        await move(
            MoveScheduleEventInput(
                event_id=event_id, place_after_entry_id=data.place_after_entry_id
            )
        )
