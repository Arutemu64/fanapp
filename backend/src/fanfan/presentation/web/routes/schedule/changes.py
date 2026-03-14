from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException
from starlette import status

from fanfan.application.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
    ListScheduleChangesResult,
)
from fanfan.application.schedule_mgmt.undo_change import (
    UndoScheduleChange,
    UndoScheduleChangeCommand,
)
from fanfan.core.exceptions.schedule import ScheduleChangeNotFound
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.presentation.web.schemas.error import ErrorMessage

changes_router = APIRouter(prefix="/changes")


@changes_router.get(
    "",
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


@changes_router.delete(
    "/{schedule_change_id}",
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
            status_code=status.HTTP_404_NOT_FOUND, detail=e.message
        ) from e
