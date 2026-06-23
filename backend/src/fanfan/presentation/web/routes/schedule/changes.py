from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Path, Query

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.schedule_mgmt.list_schedule_changes import (
    ListScheduleChanges,
    ListScheduleChangesInput,
    ListScheduleChangesResult,
)
from fanfan.application.interactors.schedule_mgmt.undo_schedule_change import (
    UndoScheduleChange,
    UndoScheduleChangeInput,
)
from fanfan.core.vo.schedule_change import ScheduleChangeId
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

changes_router = APIRouter(
    prefix="/changes",
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@changes_router.get(
    "/",
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
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListScheduleChangesResult:
    data = ListScheduleChangesInput(pagination=Pagination(limit=limit, offset=offset))
    return await interactor(data)


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
    schedule_change_id: Annotated[
        ScheduleChangeId,
        Path(description="Schedule change ID to undo."),
    ],
    interactor: FromDishka[UndoScheduleChange],
) -> None:
    await interactor(UndoScheduleChangeInput(schedule_change_id=schedule_change_id))
