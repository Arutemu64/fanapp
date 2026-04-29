from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.schedule.get_schedule import (
    GetSchedule,
    GetScheduleOutput,
)

public_router = APIRouter()


@public_router.get(
    path="/",
    summary="Get current schedule",
    description="Retrieves the full schedule using the GetSchedule interactor.",
    responses={
        200: {
            "model": GetScheduleOutput,
            "description": "Schedule retrieved successfully.",
        },
    },
)
@inject
async def get_schedule(
    interactor: FromDishka[GetSchedule],
) -> GetScheduleOutput:
    return await interactor()
