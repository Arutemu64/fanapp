from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, UploadFile

from fanfan.adapters.parsers.schedule import parse_schedule_from_excel
from fanfan.application.interactors.schedule_mgmt.import_schedule import (
    ImportSchedule,
    ImportScheduleInput,
)

importing_router = APIRouter()


@importing_router.post(
    "/import",
    status_code=201,
)
@inject
async def import_schedule(
    file: UploadFile,
    interactor: FromDishka[ImportSchedule],
) -> None:
    # Parse once here to keep the interactor focused on business logic.
    schedule = parse_schedule_from_excel(file=file.file)
    await interactor(ImportScheduleInput(schedule=schedule))
