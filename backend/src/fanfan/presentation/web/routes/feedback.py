from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from fanfan.application.dto.page import Pagination
from fanfan.application.interactors.feedback.list_feedback import (
    ListFeedback,
    ListFeedbackInput,
    ListFeedbackResult,
)
from fanfan.application.interactors.feedback.submit_feedback import (
    SubmitFeedback,
    SubmitFeedbackInput,
    SubmitFeedbackOutput,
)
from fanfan.presentation.web.responses import AUTH_RESPONSES
from fanfan.presentation.web.security import session_security

feedback_router = APIRouter(
    prefix="/feedback",
    dependencies=[session_security],
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


@feedback_router.get(
    "/",
    summary="List app feedback",
    description="Returns a paginated list of feedback submitted by users, newest "
    "first. Requires the feedback:read permission.",
    responses={
        200: {
            "model": ListFeedbackResult,
            "description": "Feedback retrieved successfully.",
        },
    },
)
@inject
async def list_feedback(
    interactor: FromDishka[ListFeedback],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ListFeedbackResult:
    data = ListFeedbackInput(pagination=Pagination(limit=limit, offset=offset))
    return await interactor(data)
