from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.schedule.get_schedule import (
    GetSchedule,
    GetScheduleResult,
)
from fanfan.application.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
    ListScheduleChangesResult,
)
from fanfan.application.schedule_mgmt.move_event import (
    MoveScheduleEvent,
    MoveScheduleEventCommand,
    MoveScheduleEventResult,
)
from fanfan.application.schedule_mgmt.set_current_event import (
    SetCurrentScheduleEvent,
    SetCurrentScheduleEventCommand,
    SetCurrentScheduleEventResult,
)
from fanfan.application.schedule_mgmt.undo_change import (
    UndoScheduleChange,
    UndoScheduleChangeCommand,
)
from fanfan.application.schedule_mgmt.update_event_skip import (
    UpdateScheduleEventSkip,
    UpdateScheduleEventSkipCommand,
    UpdateScheduleEventSkipResult,
)
from fanfan.application.subscriptions.create_subscription import (
    CreateSubscription,
    CreateSubscriptionCommand,
)
from fanfan.application.subscriptions.delete_subscription import (
    DeleteSubscription,
    DeleteSubscriptionCommand,
)
from fanfan.core.dto.subscription import SubscriptionFullDTO
from fanfan.core.exceptions.schedule import (
    CurrentEventNotAllowed,
    EventNotFound,
    SameEventsAreNotAllowed,
    ScheduleChangeNotFound,
    ScheduleEditTooFast,
    SkippedEventNotAllowed,
)
from fanfan.core.exceptions.subscriptions import (
    SubscriptionAlreadyExist,
    SubscriptionNotFound,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.core.vo.schedule_event import ScheduleEventId
from fanfan.core.vo.subscription import SubscriptionId
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.schemas.schedule import (
    MoveScheduleEventRequest,
)

schedule_router = APIRouter(tags=["Schedule"], prefix="/schedule")


@schedule_router.get(
    path="",
    status_code=200,
    summary="Get current schedule",
    description="Retrieves the full schedule using the GetSchedule interactor.",
    responses={
        200: {
            "model": GetScheduleResult,
            "description": "Schedule retrieved successfully.",
        },
    },
)
@inject
async def get_schedule(
    interactor: FromDishka[GetSchedule],
) -> GetScheduleResult:

    return await interactor()


@schedule_router.patch(
    "/{event_id}/current",
    status_code=200,
    summary="Set specific event as current",
    description="Updates the schedule state to mark a specific event as active. "
    "Validates timing and event status.",
    responses={
        200: {
            "model": SetCurrentScheduleEventResult,
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
    event_id: ScheduleEventId,
    interactor: FromDishka[SetCurrentScheduleEvent],
) -> SetCurrentScheduleEventResult:
    try:
        result = await interactor(SetCurrentScheduleEventCommand(event_id=event_id))
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SkippedEventNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=e.message
        ) from e
    except ScheduleEditTooFast as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
            headers={"Retry-After": str(e.retry_after)},
        ) from e
    else:
        return result


@schedule_router.delete(
    "/current",
    status_code=200,
    summary="Unset current schedule event",
    description="Clears the currently active event from the schedule. "
    "Subject to rate limiting.",
    responses={
        200: {
            "model": SetCurrentScheduleEventResult,
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
) -> SetCurrentScheduleEventResult:
    try:
        result = await interactor(SetCurrentScheduleEventCommand(event_id=None))
    except ScheduleEditTooFast as e:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.message,
            headers={"Retry-After": str(e.retry_after)},
        ) from e
    else:
        return result


@schedule_router.patch(
    "/{event_id}/move",
    status_code=200,
    summary="Reorder schedule event",
    description="Moves an event to a new position in the sequence, "
    "specifically after the provided event ID.",
    responses={
        200: {
            "model": MoveScheduleEventResult,
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
    event_id: ScheduleEventId,
    data: MoveScheduleEventRequest,
    interactor: FromDishka[MoveScheduleEvent],
) -> MoveScheduleEventResult:
    try:
        result = await interactor(
            MoveScheduleEventCommand(
                event_id=event_id, place_after_event_id=data.place_after_event_id
            )
        )
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SameEventsAreNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    else:
        return result


@schedule_router.patch(
    "/{event_id}/skip",
    status_code=200,
    summary="Skip a schedule event",
    description="Marks a specific event as skipped. "
    "Note: the currently active event cannot be skipped.",
    responses={
        200: {
            "model": UpdateScheduleEventSkipResult,
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
    event_id: ScheduleEventId,
    interactor: FromDishka[UpdateScheduleEventSkip],
) -> UpdateScheduleEventSkipResult:
    try:
        result = await interactor(
            UpdateScheduleEventSkipCommand(event_id=event_id, is_skipped=True)
        )
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except CurrentEventNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    else:
        return result


@schedule_router.patch(
    "/{event_id}/unskip",
    status_code=200,
    summary="Unskip a schedule event",
    description="Restores a previously skipped event back into "
    "the active schedule sequence.",
    responses={
        200: {
            "model": UpdateScheduleEventSkipResult,
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
    event_id: ScheduleEventId,
    interactor: FromDishka[UpdateScheduleEventSkip],
) -> UpdateScheduleEventSkipResult:
    try:
        result = await interactor(
            UpdateScheduleEventSkipCommand(event_id=event_id, is_skipped=False)
        )
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except CurrentEventNotAllowed as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        ) from e
    else:
        return result


@schedule_router.get(
    "/changes",
    status_code=200,
    summary="List schedule audit log",
    description="Returns a history of all modifications made to the schedule, "
    "including skips, moves, and status changes.",
    responses={
        200: {
            "model": ListScheduleChangesResult,
            "description": "Schedule changes retrieved successfully.",
        },
    },
)
@inject
async def list_schedule_changes(
    interactor: FromDishka[ListScheduleChanges],
) -> ListScheduleChangesResult:
    return await interactor()


@schedule_router.delete(
    "/changes/{schedule_change_id}",
    status_code=204,
    summary="Undo a specific schedule change",
    description="Reverts a previously made change to the schedule "
    "using its unique change ID.",
    responses={
        204: {"description": "Change successfully undone."},
        404: {
            "model": ErrorMessage,
            "description": "Schedule change ID not found.",
        },
    },
)
@inject
async def undo_schedule_change(
    schedule_change_id: ScheduleChangeId,
    interactor: FromDishka[UndoScheduleChange],
) -> None:
    try:
        await interactor(
            UndoScheduleChangeCommand(schedule_change_id=schedule_change_id)
        )
    except ScheduleChangeNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    else:
        return


@schedule_router.post(
    "/subscriptions",
    status_code=201,
    summary="Create a new event subscription",
    description="Subscribes the current user to a specific schedule event. "
    "Prevents duplicate subscriptions.",
    responses={
        201: {
            "model": SubscriptionFullDTO,
            "description": "Subscription created successfully.",
        },
        404: {
            "model": ErrorMessage,
            "description": "Event ID does not exist.",
        },
        409: {
            "model": ErrorMessage,
            "description": "Subscription for this event already exists.",
        },
    },
)
@inject
async def new_subscription(
    data: CreateSubscriptionCommand,
    interactor: FromDishka[CreateSubscription],
) -> SubscriptionFullDTO:
    try:
        result = await interactor(data)
    except EventNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    except SubscriptionAlreadyExist as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.message,
        ) from e
    else:
        return result


@schedule_router.delete(
    "/subscriptions/{subscription_id}",
    status_code=204,
    summary="Remove a subscription",
    description="Deletes an existing subscription by its unique ID.",
    responses={
        204: {"description": "Subscription deleted successfully."},
        404: {
            "model": ErrorMessage,
            "description": "Subscription ID not found.",
        },
    },
)
@inject
async def delete_subscription(
    subscription_id: SubscriptionId,
    interactor: FromDishka[DeleteSubscription],
) -> None:
    try:
        await interactor(DeleteSubscriptionCommand(subscription_id=subscription_id))
    except SubscriptionNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        ) from e
    else:
        return
