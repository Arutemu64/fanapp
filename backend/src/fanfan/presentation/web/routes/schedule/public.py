from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.schedule.get_schedule import GetSchedule, GetScheduleResult

public_router = APIRouter()


@public_router.get(
    path="/",
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
