from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from fanfan.adapters.parsers.schedule import parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
)
from fanfan.application.services.current_user import CurrentUserProvider
from fanfan.application.services.permissions import PermissionService
from fanfan.core.vo.permission import Permission
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.schemas.error import ErrorMessage
from fanfan.presentation.web.security import session_security

# A real convention schedule is a few hundred rows — well under a megabyte. Cap
# generously so a legitimate import never trips it, while a hostile multi-hundred-
# MB body is rejected before the in-memory polars parse.
_MAX_IMPORT_BYTES = 5 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",  # some browsers send this for .xlsx
    }
)


def _ensure_within_size_limit(file: UploadFile) -> None:
    if file.size is not None and file.size > _MAX_IMPORT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Файл расписания слишком большой.",
        )
    filename = file.filename or ""
    if not filename.lower().endswith(".xlsx") or (
        file.content_type is not None
        and file.content_type not in _ALLOWED_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Ожидается файл .xlsx.",
        )


importing_router = APIRouter(
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@importing_router.post(
    "/import",
    status_code=201,
    responses={
        400: {
            "model": ErrorMessage,
            "description": "The spreadsheet could not be read as a schedule.",
        },
        413: {
            "model": ErrorMessage,
            "description": "The uploaded file exceeds the allowed size limit.",
        },
        415: {
            "model": ErrorMessage,
            "description": "The uploaded file is not a supported spreadsheet (.xlsx).",
        },
    },
)
@inject
async def import_schedule(
    file: Annotated[UploadFile, File(description="Excel file with schedule data.")],
    interactor: FromDishka[ImportSchedule],
    current_user_provider: FromDishka[CurrentUserProvider],
    perm_service: FromDishka[PermissionService],
) -> None:
    # Authorize before reading/parsing the upload: the parse buffers the whole
    # file and runs a CPU-heavy synchronous read, so an unauthorized caller must
    # be rejected before it, not by the interactor afterwards.
    current_user = await current_user_provider.require_user()
    await perm_service.ensure(user=current_user, permission=Permission.SCHEDULE_IMPORT)
    _ensure_within_size_limit(file)
    # Parse in a worker thread because polars/fastexcel are synchronous libraries.
    # This keeps the async FastAPI event loop responsive during file imports.
    schedule = await run_in_threadpool(parse_schedule_from_excel, file.file)
    await interactor(ImportScheduleInput(schedule=schedule))
