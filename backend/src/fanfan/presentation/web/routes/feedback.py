from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.feedback.submit_feedback import (
    SubmitFeedback,
    SubmitFeedbackInput,
    SubmitFeedbackOutput,
)

feedback_router = APIRouter(prefix="/feedback")


@feedback_router.post(
    "/",
    status_code=201,
    summary="Submit app feedback",
    description="Submits free-text feedback about the app from the current user.",
    responses={
        201: {
            "model": SubmitFeedbackOutput,
            "description": "Feedback submitted successfully.",
        },
    },
)
@inject
async def submit_feedback(
    data: SubmitFeedbackInput,
    interactor: FromDishka[SubmitFeedback],
) -> SubmitFeedbackOutput:
    return await interactor(data)
