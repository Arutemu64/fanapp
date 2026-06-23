from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from fanfan.application.interactors.feedback.submit_feedback import (
    SubmitFeedback,
    SubmitFeedbackInput,
    SubmitFeedbackOutput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import require_session_docs

feedback_router = APIRouter(
    prefix="/feedback",
    dependencies=[require_session_docs],
    responses=AUTH_RESPONSES,
)


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
