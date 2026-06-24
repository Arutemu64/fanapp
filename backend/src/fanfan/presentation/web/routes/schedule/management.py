from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path

from fanfan.application.interactors.schedule_mgmt.move_schedule_item import (
    MoveScheduleItem,
    MoveScheduleItemInput,
)
from fanfan.application.interactors.schedule_mgmt.set_current_schedule_item import (
    SetCurrentScheduleItem,
    SetCurrentScheduleItemInput,
)
from fanfan.application.interactors.schedule_mgmt.update_schedule_item_skip import (
    UpdateScheduleItemSkip,
    UpdateScheduleItemSkipInput,
)
from fanfan.core.vo.schedule_item import ScheduleItemId
from fanfan.presentation.web.responses import AUTH_RESPONSES, RATE_LIMIT_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.schemas.schedule import (
    MoveScheduleItemRequest,
    UpdateScheduleItemRequest,
)
from fanfan.presentation.web.security import session_security

# Every interactor here takes the shared announcement rate lock, so 429 is a
# possible response for all of them — declare it once at the router level.
management_router = APIRouter(
    dependencies=[session_security],
    responses={**AUTH_RESPONSES, **RATE_LIMIT_RESPONSES},
)


@management_router.patch(
    "/{schedule_item_id}/current",
    status_code=204,
    summary="Set specific event as current",
    description="Updates the schedule state to mark a specific event as active. "
    "Validates timing and event status.",
    responses={
        204: {"description": "Event set as current successfully."},
        400: {
            "model": ErrorMessage,
            "description": "Event is skipped or invalid for this operation.",
        },
        404: {"model": ErrorMessage, "description": "Event ID not found."},
    },
)
@inject
async def set_event_as_current(
    schedule_item_id: Annotated[ScheduleItemId, Path(description="Schedule item ID.")],
    interactor: FromDishka[SetCurrentScheduleItem],
) -> None:
    await interactor(SetCurrentScheduleItemInput(schedule_item_id=schedule_item_id))


@management_router.delete(
    "/current",
    status_code=204,
    summary="Unset current schedule event",
    description="Clears the currently active event from the schedule. "
    "Subject to rate limiting.",
    responses={
        204: {"description": "Current event cleared successfully."},
    },
)
@inject
async def uncheck_current_event(
    interactor: FromDishka[SetCurrentScheduleItem],
) -> None:
    await interactor(SetCurrentScheduleItemInput(schedule_item_id=None))


@management_router.patch(
    "/{schedule_item_id}/move",
    status_code=204,
    summary="Reorder schedule event",
    description="Moves an event to a new position in the sequence, "
    "specifically after the provided event ID.",
    responses={
        204: {"description": "Event moved successfully."},
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
async def move_schedule_item(
    schedule_item_id: Annotated[ScheduleItemId, Path(description="Schedule item ID.")],
    data: MoveScheduleItemRequest,
    interactor: FromDishka[MoveScheduleItem],
) -> None:
    await interactor(
        MoveScheduleItemInput(
            schedule_item_id=schedule_item_id,
            place_after_schedule_item_id=data.place_after_schedule_item_id,
        )
    )


@management_router.patch(
    "/{schedule_item_id}",
    status_code=204,
    summary="Update a schedule event",
    description="Updates a schedule event's skip state. Set `is_skipped` to true to "
    "skip the event or false to restore it. Note: the currently active event cannot "
    "be skipped.",
    responses={
        204: {"description": "Event updated successfully."},
        400: {
            "model": ErrorMessage,
            "description": "Cannot skip the current active event.",
        },
        404: {"model": ErrorMessage, "description": "Event ID not found."},
    },
)
@inject
async def update_schedule_item(
    schedule_item_id: Annotated[ScheduleItemId, Path(description="Schedule item ID.")],
    data: UpdateScheduleItemRequest,
    interactor: FromDishka[UpdateScheduleItemSkip],
) -> None:
    await interactor(
        UpdateScheduleItemSkipInput(
            schedule_item_id=schedule_item_id, is_skipped=data.is_skipped
        )
    )
