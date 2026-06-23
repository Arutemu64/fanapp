from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path

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
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.schemas.schedule import MoveScheduleEventRequest
from fanfan.presentation.web.security import require_session_docs

management_router = APIRouter(
    dependencies=[require_session_docs],
    responses=AUTH_RESPONSES,
)


@management_router.patch(
    "/{event_id}/current",
    summary="Set specific event as current",
    description="Updates the schedule state to mark a specific event as active. "
    "Validates timing and event status.",
    responses={
        200: {
            "model": None,
            "description": "Event set as current successfully.",
        },
        400: {
            "model": ErrorMessage,
            "description": "Event is skipped or invalid for this operation.",
        },
        404: {"model": ErrorMessage, "description": "Event ID not found."},
        429: {
            "model": ErrorMessage,
            "description": "Rate limited — editing too fast.",
            "headers": {
                "Retry-After": {
                    "schema": {"type": "integer"},
                    "description": "Seconds to wait before retrying.",
                }
            },
        },
    },
)
@inject
async def set_event_as_current(
    event_id: Annotated[ScheduleEventId, Path(description="Schedule event ID.")],
    interactor: FromDishka[SetCurrentScheduleEvent],
) -> None:
    await interactor(SetCurrentScheduleEventInput(event_id=event_id))


@management_router.delete(
    "/current",
    summary="Unset current schedule event",
    description="Clears the currently active event from the schedule. "
    "Subject to rate limiting.",
    responses={
        200: {
            "model": None,
            "description": "Current event cleared successfully.",
        },
        429: {
            "model": ErrorMessage,
            "description": "Rate limited — editing too fast.",
            "headers": {
                "Retry-After": {
                    "description": "Seconds to wait before retrying.",
                    "schema": {"type": "integer"},
                }
            },
        },
    },
)
@inject
async def uncheck_current_event(
    interactor: FromDishka[SetCurrentScheduleEvent],
) -> None:
    await interactor(SetCurrentScheduleEventInput(event_id=None))


@management_router.patch(
    "/{event_id}/move",
    summary="Reorder schedule event",
    description="Moves an event to a new position in the sequence, "
    "specifically after the provided event ID.",
    responses={
        200: {
            "model": None,
            "description": "Event moved successfully.",
        },
        400: {
            "model": ErrorMessage,
            "description": "Invalid move: target and destination are the same.",
        },
        404: {
            "model": ErrorMessage,
            "description": "Event to move or target neighbor event was not found.",
        },
    },
)
@inject
async def move_schedule_event(
    event_id: Annotated[ScheduleEventId, Path(description="Schedule event ID.")],
    data: MoveScheduleEventRequest,
    interactor: FromDishka[MoveScheduleEvent],
) -> None:
    await interactor(
        MoveScheduleEventInput(
            event_id=event_id, place_after_event_id=data.place_after_event_id
        )
    )


@management_router.patch(
    "/{event_id}/skip",
    summary="Skip a schedule event",
    description="Marks a specific event as skipped. "
    "Note: the currently active event cannot be skipped.",
    responses={
        200: {
            "model": None,
            "description": "Event marked as skipped.",
        },
        400: {
            "model": ErrorMessage,
            "description": "Cannot skip the current active event.",
        },
        404: {"model": ErrorMessage, "description": "Event ID not found."},
    },
)
@inject
async def skip_schedule_event(
    event_id: Annotated[ScheduleEventId, Path(description="Schedule event ID.")],
    interactor: FromDishka[UpdateScheduleEventSkip],
) -> None:
    await interactor(UpdateScheduleEventSkipInput(event_id=event_id, is_skipped=True))


@management_router.patch(
    "/{event_id}/unskip",
    summary="Unskip a schedule event",
    description="Restores a previously skipped event back into "
    "the active schedule sequence.",
    responses={
        200: {
            "model": None,
            "description": "Event restored to active schedule.",
        },
        400: {
            "model": ErrorMessage,
            "description": "Event state cannot be modified in its current context.",
        },
        404: {"model": ErrorMessage, "description": "Event ID not found."},
    },
)
@inject
async def unskip_schedule_event(
    event_id: Annotated[ScheduleEventId, Path(description="Schedule event ID.")],
    interactor: FromDishka[UpdateScheduleEventSkip],
) -> None:
    await interactor(UpdateScheduleEventSkipInput(event_id=event_id, is_skipped=False))
