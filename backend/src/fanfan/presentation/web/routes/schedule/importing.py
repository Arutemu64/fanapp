from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, File, UploadFile
from starlette.concurrency import run_in_threadpool

from fanfan.adapters.parsers.schedule import parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import session_security

importing_router = APIRouter(
    dependencies=[session_security],
    responses=AUTH_RESPONSES,
)


@importing_router.post(
    "/import",
    status_code=201,
)
@inject
async def import_schedule(
    file: Annotated[UploadFile, File(description="Excel file with schedule data.")],
    interactor: FromDishka[ImportSchedule],
) -> None:
    # Parse in a worker thread because Pandas/OpenPyXL are synchronous libraries.
    # This keeps the async FastAPI event loop responsive during file imports.
    schedule = await run_in_threadpool(parse_schedule_from_excel, file.file)
    await interactor(ImportScheduleInput(schedule=schedule))
