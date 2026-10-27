from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from fanfan.adapters.parsers.schedule import parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
)
from fanfan.application.interactors.schedule_mgmt.schedule_settings import (
    GetScheduleSettings,
    ScheduleSettingsDTO,
    UpdateScheduleSettings,
    UpdateScheduleSettingsInput,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.exceptions.schedule import (
    InvalidScheduleFile,
    InvalidScheduleFileReason,
)
from fanfan.core.vo.permission import Permission
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import InvalidScheduleFileProblem
from fanfan.presentation.web.security import session_security

_MAX_IMPORT_BYTES = 5 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    }
)


def _ensure_valid_upload(file: UploadFile) -> None:
    if file.size is not None and file.size > _MAX_IMPORT_BYTES:
        raise InvalidScheduleFile(reason=InvalidScheduleFileReason.FILE_TOO_LARGE)
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx") or (
        file.content_type is not None
        and file.content_type not in _ALLOWED_CONTENT_TYPES
    ):
        raise InvalidScheduleFile(
            reason=InvalidScheduleFileReason.UNSUPPORTED_FILE_TYPE
        )


class ImportScheduleForm(BaseModel):
    """Multipart body of POST /schedule/import, named so the spec and the
    generated client don't carry FastAPI's ``Body_import_schedule``."""

    file: UploadFile = Field(description="Excel file with schedule data.")


importing_router = APIRouter(
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@importing_router.post(
    "/import",
    status_code=204,
    summary="Import schedule",
    description=(
        "Syncs the programme to the rows of an .xlsx spreadsheet (the "
        "downloadable template): matching entries are updated in place, new "
        "rows added and missing ones deleted. Requires 'schedule:setup'."
    ),
    responses={
        204: {"description": "Schedule imported."},
        400: {
            "model": InvalidScheduleFileProblem,
            "description": "The upload is not an acceptable schedule spreadsheet: "
            "too large, the wrong type, or unreadable as a schedule.",
        },
    },
)
@inject
async def import_schedule(
    form: Annotated[ImportScheduleForm, File()],
    interactor: FromDishka[ImportSchedule],
    current_user_provider: FromDishka[CurrentUserProvider],
    perm_service: FromDishka[PermissionService],
) -> None:
    current_user = await current_user_provider.require_user()
    await perm_service.ensure(user=current_user, permission=Permission.SCHEDULE_SETUP)
    _ensure_valid_upload(form.file)
    schedule = await run_in_threadpool(parse_schedule_from_excel, form.file.file)
    await interactor(ImportScheduleInput(schedule=schedule))


@importing_router.get(
    "/settings",
    summary="Get schedule settings",
    description=(
        "Returns the cooldown between announced schedule edits and the "
        "changeover added per act to wait estimates. Requires 'schedule:setup'."
    ),
    responses={
        200: {"description": "Schedule settings retrieved successfully."},
    },
)
@inject
async def get_schedule_settings(
    interactor: FromDishka[GetScheduleSettings],
) -> ScheduleSettingsDTO:
    return await interactor()


@importing_router.patch(
    "/settings",
    status_code=204,
    summary="Update schedule settings",
    description=(
        "Updates the schedule settings; an omitted field is left as is. "
        "Requires 'schedule:setup'."
    ),
    responses={
        204: {"description": "Schedule settings saved."},
    },
)
@inject
async def update_schedule_settings(
    data: UpdateScheduleSettingsInput,
    interactor: FromDishka[UpdateScheduleSettings],
) -> None:
    await interactor(data)
